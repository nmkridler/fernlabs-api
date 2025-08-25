"""
Standalone AI-powered workflow agent using pydantic-graph
"""

from typing import List, Dict, Any, Optional, Annotated
import uuid
import asyncio
import re
from html import escape
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from pydantic_ai import Agent, RunContext
from pydantic_ai.providers import Provider
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.google import GoogleModel
from pydantic import BaseModel
from loguru import logger
from pydantic_graph import BaseNode, End, Graph, GraphRunContext, Edge

from fernlabs_api.settings import APISettings
from fernlabs_api.db.model import Plan, Workflow, AgentCall, Project

logger.add("async_log.log", enqueue=True)
STEP_RE = re.compile(r"^\s*(\d+)\.\s*([^:]+?)(?:\s*:\s*(.*))?\s*$")


def _model_factory(model_name: str, provider_name: str, api_key: str) -> Provider:
    """Create a provider based on the model name"""
    if provider_name == "mistral":
        return MistralModel(model_name, provider=MistralProvider(api_key=api_key))
    elif provider_name == "openai":
        return OpenAIModel(model_name, provider=OpenAIProvider(api_key=api_key))
    elif provider_name == "google":
        return GoogleModel(model_name, provider=GoogleProvider(api_key=api_key))

    raise ValueError(f"Unsupported provider: {provider_name}")


class PlanDependencies(BaseModel):
    """Dependencies for plan creation including user context and database access"""

    user_id: uuid.UUID
    project_id: uuid.UUID
    chat_history: List[
        Dict[str, str]
    ]  # List of {"role": "user/assistant", "content": "message"}
    db: Any  # Accept any type for testing flexibility

    model_config = {"arbitrary_types_allowed": True}


class PlanResponse(BaseModel):
    """Response containing the created or edited plan"""

    plan: str
    mermaid_chart: str


class WorkflowState(BaseModel):
    """State maintained throughout the workflow execution"""

    user_id: uuid.UUID
    project_id: uuid.UUID
    chat_history: List[Dict[str, str]] = field(default_factory=list)
    current_plan: Optional[str] = None
    mermaid_chart: Optional[str] = None
    plan_needs_improvement: bool = False
    followup_question: Optional[str] = None
    user_response: Optional[str] = None
    final_plan: Optional[PlanResponse] = None
    db: Any = None

    model_config = {"arbitrary_types_allowed": True}


class WorkflowDependencies(BaseModel):
    """Dependencies injected into the workflow"""

    settings: APISettings
    db: Session

    model_config = {"arbitrary_types_allowed": True}


def _parse_plan_into_steps(plan_text: str) -> List[str]:
    """Parse the generated plan text into individual steps"""
    # Simple parsing - split by numbered lists or bullet points
    lines = plan_text.split("\n")
    steps = []
    current_step = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if this is a new step (starts with number, bullet, or is a phase header)
        if (
            line[0].isdigit()
            and line[1] in [".", ")", " "]
            or line.startswith(("-", "•", "*"))
            or line.isupper()  # Phase headers are often in caps
            or line.endswith(":")
            or line.startswith("Phase")
            or line.startswith("Step")
        ):
            if current_step:
                steps.append(current_step.strip())
            current_step = line
        else:
            current_step += " " + line

    # Add the last step
    if current_step:
        steps.append(current_step.strip())

    # If no clear steps found, split by paragraphs
    if len(steps) <= 1:
        steps = [step.strip() for step in plan_text.split("\n\n") if step.strip()]

    return steps


def _generate_plan_mermaid_chart(plan_steps: List[str]) -> str:
    """
    Parse lines like '1. Load Data: load the csv data' into a Mermaid flowchart TD.
    - Lines may omit the description ('2. Transform Data')
    - Ignores blank/comment lines
    - Orders nodes by the numeric prefix
    - Escapes characters that could break Mermaid/HTML

    Args:
        text: the numbered steps block
        title_desc_sep: separator between title and description in node label (default: HTML <br/>)

    Returns:
        str: Mermaid code block (string) for a flowchart TD
    """
    steps = []
    for line in plan_steps:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = STEP_RE.match(line)
        if not m:
            # skip non-matching lines gracefully
            continue
        n, title, desc = m.group(1), m.group(2).strip(), (m.group(3) or "").strip()
        # Escape for safety; Mermaid supports simple HTML in labels
        title = escape(title)
        desc = escape(desc)
        steps.append((int(n), title, desc))

    if not steps:
        raise ValueError(
            "No steps parsed. Make sure lines look like '1. Title: description'."
        )

    # Sort by the numeric index just in case lines are out of order
    steps.sort(key=lambda x: x[0])

    # Build nodes
    node_lines = []
    edge_lines = []

    for idx, (n, title, desc) in enumerate(steps, start=1):
        node_id = f"S{idx}"
        label = title if not desc else f"{title}<br/>{desc[:20]}..."
        node_lines.append(f'    {node_id}["{label}"]:::big')

        if idx > 1:
            edge_lines.append(f"    S{idx - 1} --> {node_id}")

    # Assemble Mermaid
    mermaid = ["flowchart TD"]
    mermaid.extend(node_lines)
    mermaid.extend(edge_lines)
    mermaid.extend(["classDef big font-size:18px;"])

    return "\n".join(mermaid)


def _save_mermaid_chart_to_project(
    db: Session, project_id: uuid.UUID, mermaid_chart: str
):
    """Save the mermaid chart to the project in the database"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        project.mermaid_chart = mermaid_chart
        db.commit()
        logger.info(f"Saved mermaid chart to project {project_id}")


@dataclass
class CreatePlan(BaseNode[WorkflowState, WorkflowDependencies]):
    """Create initial project plan from conversation history"""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDependencies]
    ) -> Annotated["AssessPlan", Edge(label="Plan Created")]:
        """Create a comprehensive project plan from description and requirements"""

        # Set project status to loading
        self._update_project_status(ctx.deps.db, ctx.state.project_id, "loading")

        # Initialize the agent for plan creation
        agent = Agent(
            _model_factory(
                ctx.deps.settings.api_model_name,
                ctx.deps.settings.api_model_provider,
                ctx.deps.settings.api_model_key,
            ),
            output_type=PlanResponse,
            system_prompt=(
                "You are an expert workflow designer and project planner. "
                "Create high level project plans suitable for workflow automation. "
                "Enumerate the steps in the plan in a numbered list. "
                "Also generate a Mermaid flowchart diagram that visualizes the workflow steps."
            ),
        )

        # Build the prompt with chat history context
        chat_context = "\n".join(
            [
                f"{msg['role'].title()}: {msg['content']}"
                for msg in ctx.state.chat_history
            ]
        )

        prompt = f"""
        Based on the following conversation history create a high level project plan:

        Conversation History:
        {chat_context}

        Create a high level plan that outlines the overall flow of the project.
        Be concise, to the point, and only include the most important steps.
        Give each step a succinct title formatted as title: description.
        For example: Load Data: load the data from the csv file.

        Also generate a Mermaid flowchart diagram that visualizes these steps.
        The diagram should show the sequential flow from start to end.
        Use the format: flowchart TD with numbered steps and arrows connecting them.
        """

        # Generate the plan
        result = await agent.run(prompt)
        plan_response = result.output

        # Store the plan in state
        ctx.state.current_plan = plan_response.plan

        # Parse the plan into steps and save to database
        plan_steps = _parse_plan_into_steps(plan_response.plan)
        ctx.state.mermaid_chart = _generate_plan_mermaid_chart(plan_steps)

        # Save each step to the database
        for step_id, step_text in enumerate(plan_steps, 1):
            logger.info(f"Saving step {step_id}: {step_text}")
            plan_entry = Plan(
                id=uuid.uuid4(),
                user_id=ctx.state.user_id,
                project_id=ctx.state.project_id,
                step_id=step_id,
                text=step_text,
            )
            ctx.deps.db.add(plan_entry)

        ctx.deps.db.commit()

        # Save the mermaid chart to the project
        _save_mermaid_chart_to_project(
            ctx.deps.db, ctx.state.project_id, ctx.state.mermaid_chart
        )

        # Log the agent call
        await self._log_agent_call(
            ctx.deps.db, ctx.state.project_id, prompt, str(plan_response)
        )

        return AssessPlan()

    def _update_project_status(self, db: Session, project_id: uuid.UUID, status: str):
        """Update the project status in the database"""
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = status
            db.commit()

    async def _log_agent_call(
        self, db: Session, project_id: uuid.UUID, prompt: str, response: str
    ):
        """Log an agent call and response to the database"""
        agent_call = AgentCall(
            id=uuid.uuid4(),
            project_id=project_id,
            prompt=prompt,
            response=response,
        )
        db.add(agent_call)
        db.commit()


@dataclass
class AssessPlan(BaseNode[WorkflowState, WorkflowDependencies]):
    """Assess the created plan and determine if follow-up questions are needed"""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDependencies]
    ) -> (
        Annotated["WaitForUserInput", Edge(label="Needs Followup")]
        | Annotated["End", Edge(label="Plan Complete")]
    ):
        """Assess the plan and determine if improvements are needed"""

        # Initialize the assessment agent
        agent = Agent(
            _model_factory(
                ctx.deps.settings.api_model_name,
                ctx.deps.settings.api_model_provider,
                ctx.deps.settings.api_model_key,
            ),
            output_type=str,
            system_prompt=(
                "You are an expert project planner. Analyze plans and identify critical gaps "
                "that need follow-up questions to improve the plan quality."
            ),
        )

        # Build the prompt to analyze the existing plan
        chat_context = "\n".join(
            [
                f"{msg['role'].title()}: {msg['content']}"
                for msg in ctx.state.chat_history
            ]
        )

        prompt = f"""
        Analyze the following existing plan and conversation history to identify if a follow-up question is needed:

        Existing Plan:
        {ctx.state.current_plan}

        Conversation History:
        {chat_context}

        Based on this analysis, please identify the most important question to ask to improve the plan:

        Focus on asking about high level details that are not covered in the plan. Save
        implementation details for later.

        If the plan is comprehensive and doesn't need follow-up, respond with "PLAN_COMPLETE".
        Otherwise, return the follow-up question.
        """

        # Use the agent to analyze the plan
        result = await agent.run(prompt)
        assessment = result.output

        # Log the assessment call
        await self._log_agent_call(
            ctx.deps.db, ctx.state.project_id, prompt, assessment
        )

        # Check if plan needs improvement
        if "PLAN_COMPLETE" in assessment.upper():
            # Plan is complete, end the workflow
            ctx.state.final_plan = PlanResponse(
                plan=ctx.state.current_plan,
                mermaid_chart=ctx.state.mermaid_chart,
            )
            self._update_project_status(ctx.deps.db, ctx.state.project_id, "completed")
            return End(ctx.state.final_plan)
        else:
            # Plan needs improvement, store follow-up question and wait for user input
            ctx.state.plan_needs_improvement = True
            ctx.state.followup_question = assessment
            return WaitForUserInput()

    async def _log_agent_call(
        self, db: Session, project_id: uuid.UUID, prompt: str, response: str
    ):
        """Log an agent call and response to the database"""
        agent_call = AgentCall(
            id=uuid.uuid4(),
            project_id=project_id,
            prompt=prompt,
            response=response,
        )
        db.add(agent_call)
        db.commit()

    def _update_project_status(self, db: Session, project_id: uuid.UUID, status: str):
        """Update the project status in the database"""
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = status
            db.commit()


@dataclass
class WaitForUserInput(BaseNode[WorkflowState, WorkflowDependencies]):
    """Wait for user to provide response to follow-up question"""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDependencies]
    ) -> (
        Annotated["EditPlan", Edge(label="User Responded")]
        | Annotated["End", Edge(label="Waiting for Input")]
    ):
        """This node represents waiting for user input - pauses workflow and returns question"""

        # Check if we have a user response in the state
        if ctx.state.user_response and ctx.state.user_response.strip():
            logger.info(f"User response received: {ctx.state.user_response[:100]}...")

            # Update project status to indicate we're processing the response
            self._update_project_status(ctx.deps.db, ctx.state.project_id, "processing")

            # Log that we're proceeding with the user's response
            await self._log_agent_call(
                ctx.deps.db,
                ctx.state.project_id,
                "WaitForUserInput: User response received",
                f"Proceeding to EditPlan with user response: {ctx.state.user_response[:100]}...",
            )

            # We have a user response, proceed to EditPlan
            return EditPlan()
        else:
            # No user response yet, pause the workflow and return the question
            logger.info(
                "Pausing workflow - waiting for user response to follow-up question"
            )

            # Update project status to indicate we're waiting for input
            self._update_project_status(
                ctx.deps.db, ctx.state.project_id, "needs_input"
            )

            # Return End with the follow-up question to pause the workflow
            # The client will receive this and can provide a response
            return End(
                {
                    "status": "waiting_for_input",
                    "followup_question": ctx.state.followup_question,
                    "message": "Please provide additional information to continue",
                    "workflow_paused": True,
                }
            )

    async def _log_agent_call(
        self, db: Session, project_id: uuid.UUID, prompt: str, response: str
    ):
        """Log an agent call and response to the database"""
        agent_call = AgentCall(
            id=uuid.uuid4(),
            project_id=project_id,
            prompt=prompt,
            response=response,
        )
        db.add(agent_call)
        db.commit()

    def _update_project_status(self, db: Session, project_id: uuid.UUID, status: str):
        """Update the project status in the database"""
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = status
            db.commit()


@dataclass
class EditPlan(BaseNode[WorkflowState, WorkflowDependencies]):
    """Edit and improve the existing plan based on user response"""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDependencies]
    ) -> Annotated["AssessPlan", Edge(label="Plan Updated")]:
        """Edit and improve the existing project plan based on user feedback"""

        # Set project status to loading
        self._update_project_status(ctx.deps.db, ctx.state.project_id, "loading")

        # Initialize the editing agent
        agent = Agent(
            _model_factory(
                ctx.deps.settings.api_model_name,
                ctx.deps.settings.api_model_provider,
                ctx.deps.settings.api_model_key,
            ),
            output_type=PlanResponse,
            system_prompt=(
                "You are an expert project planner. Review and improve existing plans "
                "based on new requirements and feedback to create comprehensive, actionable plans. "
                "Also generate a Mermaid flowchart diagram that visualizes the improved workflow steps."
            ),
        )

        # Build the prompt with chat history context, existing plan, and user response
        chat_context = "\n".join(
            [
                f"{msg['role'].title()}: {msg['content']}"
                for msg in ctx.state.chat_history
            ]
        )

        prompt = f"""
        Review and improve the following existing project plan based on new requirements and user feedback:

        Conversation History:
        {chat_context}

        Original Plan:
        {ctx.state.current_plan}

        Follow-up Question Asked:
        {ctx.state.followup_question}

        User Response:
        {ctx.state.user_response or "No specific response provided"}

        Please analyze the existing plan and:
        1. Identify areas that need improvement or updates based on the user feedback
        2. Add missing details or phases based on new requirements
        3. Optimize the workflow structure and flow
        4. Ensure all current requirements are addressed
        5. Update timeline estimates if needed
        6. Maintain the core structure while enhancing clarity and completeness
        7. Address any gaps or inconsistencies revealed by the follow-up question

        Return an improved version of the plan that builds upon the existing structure.
        Also generate a Mermaid flowchart diagram that visualizes the improved workflow steps.
        The diagram should show the sequential flow from start to end.
        Use the format: flowchart TD with numbered steps and arrows connecting them.
        """

        # Use the agent to generate the improved plan
        result = await agent.run(prompt)
        improved_plan = result.output

        # Log the editing call
        await self._log_agent_call(
            ctx.deps.db, ctx.state.project_id, prompt, str(improved_plan)
        )

        # Parse the improved plan into steps
        improved_plan_steps = _parse_plan_into_steps(improved_plan.plan)

        # First, remove the existing plan entries for this project
        existing_plans = (
            ctx.deps.db.query(Plan)
            .filter(
                Plan.user_id == ctx.state.user_id,
                Plan.project_id == ctx.state.project_id,
            )
            .all()
        )

        for existing_plan_entry in existing_plans:
            ctx.deps.db.delete(existing_plan_entry)

        # Save the improved plan steps to the database
        for step_id, step_text in enumerate(improved_plan_steps, 1):
            plan_entry = Plan(
                id=uuid.uuid4(),
                user_id=ctx.state.user_id,
                project_id=ctx.state.project_id,
                step_id=step_id,
                text=step_text,
            )
            ctx.deps.db.add(plan_entry)

        ctx.deps.db.commit()

        # Update the current plan in state
        ctx.state.current_plan = improved_plan.plan
        ctx.state.mermaid_chart = _generate_plan_mermaid_chart(improved_plan_steps)
        ctx.state.plan_needs_improvement = False
        ctx.state.followup_question = None
        ctx.state.user_response = None

        # Save the mermaid chart to the project
        _save_mermaid_chart_to_project(
            ctx.deps.db, ctx.state.project_id, ctx.state.mermaid_chart
        )

        # Return to assessment to see if further improvements are needed
        return AssessPlan()

    async def _log_agent_call(
        self, db: Session, project_id: uuid.UUID, prompt: str, response: str
    ):
        """Log an agent call and response to the database"""
        agent_call = AgentCall(
            id=uuid.uuid4(),
            project_id=project_id,
            prompt=prompt,
            response=response,
        )
        db.add(agent_call)
        db.commit()

    def _update_project_status(self, db: Session, project_id: uuid.UUID, status: str):
        """Update the project status in the database"""
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = status
            db.commit()


# Create the workflow graph
workflow_graph = Graph(
    nodes=[CreatePlan, AssessPlan, WaitForUserInput, EditPlan], state_type=WorkflowState
)


class WorkflowAgent:
    """Refactored workflow agent using pydantic-graph"""

    def __init__(self, settings: APISettings):
        self.settings = settings
        self.graph = workflow_graph

    async def resume_workflow(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        chat_history: List[Dict[str, str]],
        db: Session,
        user_response: str,
    ) -> Dict[str, Any]:
        """Resume a workflow that was waiting for user input"""

        # Initialize workflow state with the user response
        initial_state = WorkflowState(
            user_id=user_id,
            project_id=project_id,
            chat_history=chat_history,
            db=db,
            user_response=user_response,
        )

        # Initialize dependencies
        deps = WorkflowDependencies(settings=self.settings, db=db)

        try:
            # Start from WaitForUserInput since that's where we were waiting
            result = await self.graph.run(
                WaitForUserInput(), state=initial_state, deps=deps
            )

            # Get the mermaid chart from the workflow state
            mermaid_chart = result.state.mermaid_chart if result.state else None

            return {
                "output": result.output,
                "final_state": result.state,
                "history": chat_history,
                "completed": True,
                "mermaid_chart": mermaid_chart,
            }

        except Exception as e:
            logger.error(f"Workflow resumption error: {e}")
            raise e

    async def run_workflow(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        chat_history: List[Dict[str, str]],
        db: Session,
        user_response: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the complete workflow for plan creation and improvement"""

        # Initialize workflow state
        initial_state = WorkflowState(
            user_id=user_id,
            project_id=project_id,
            chat_history=chat_history,
            db=db,
            user_response=user_response,
        )

        # Initialize dependencies
        deps = WorkflowDependencies(settings=self.settings, db=db)

        try:
            # Run the workflow
            result = await self.graph.run(CreatePlan(), state=initial_state, deps=deps)

            # Check if the workflow ended with waiting_for_input status
            if (
                hasattr(result, "output")
                and result.output
                and isinstance(result.output, dict)
                and result.output.get("status") == "waiting_for_input"
            ):
                return {
                    "output": None,
                    "final_state": result.state,
                    "history": chat_history,
                    "completed": False,
                    "waiting_for_input": True,
                    "followup_question": result.output.get("followup_question"),
                    "message": result.output.get("message"),
                    "workflow_paused": True,
                }

            # Get the mermaid chart from the workflow state
            mermaid_chart = result.state.mermaid_chart if result.state else None

            return {
                "output": result.output,
                "final_state": result.state,
                "history": chat_history,
                "completed": True,
                "mermaid_chart": mermaid_chart,
            }

        except Exception as e:
            logger.error(f"Workflow execution error: {e}")

            # Check if the error is due to waiting for user input
            if "WaitForUserInput" in str(e) or "user input" in str(e).lower():
                # Workflow is waiting for user input
                return {
                    "output": None,
                    "final_state": initial_state,
                    "history": [],
                    "completed": False,
                    "waiting_for_input": True,
                    "followup_question": initial_state.followup_question,
                    "message": "Workflow is waiting for user input to continue",
                }
            else:
                # Some other error occurred
                raise e

    def generate_mermaid_diagram(
        self,
        db: Session = None,
        user_id: uuid.UUID = None,
        project_id: uuid.UUID = None,
    ) -> str:
        """Generate a Mermaid diagram of the workflow or project plan"""
        # If we have database access and project info, generate plan-based diagram
        if db and user_id and project_id:
            plans = self.get_project_plan(db, user_id, project_id)
            if plans and len(plans) > 0:
                return self._generate_plan_mermaid_diagram(plans)

        # Fallback to workflow structure diagram
        return self.graph.mermaid_code(start_node=CreatePlan)

    def _generate_plan_mermaid_diagram(self, plans: List[Plan]) -> str:
        """Generate a Mermaid diagram from the actual project plan steps"""
        if not plans:
            return "flowchart TD\n    A[No Plan Available]"

        mermaid_lines = ["flowchart TD"]

        # Add start node
        mermaid_lines.append("    Start([Start])")

        # Add plan steps
        for i, plan in enumerate(plans):
            step_id = plan.step_id
            step_text = plan.text.strip()

            # Clean up step text for mermaid (remove special characters)
            clean_text = step_text.replace('"', "'").replace(":", " -")
            if len(clean_text) > 50:
                clean_text = clean_text[:47] + "..."

            mermaid_lines.append(f"    Step{step_id}[{step_id}. {clean_text}]")

            # Add connections
            if i == 0:
                mermaid_lines.append("    Start --> Step1")
            else:
                mermaid_lines.append(f"    Step{i} --> Step{step_id}")

        # Add end node
        mermaid_lines.append("    End([End])")
        mermaid_lines.append(f"    Step{len(plans)} --> End")

        return "\n".join(mermaid_lines)

    # Keep existing utility methods for backward compatibility
    def get_project_plan(
        self, db: Session, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> Optional[List[Plan]]:
        """Retrieve the complete plan for a project"""
        plans = (
            db.query(Plan)
            .filter(Plan.user_id == user_id, Plan.project_id == project_id)
            .order_by(Plan.step_id)
            .all()
        )

        return plans if plans else None

    def get_plan_summary(
        self, db: Session, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get a summary of the plan including step count and creation info"""
        plans = self.get_project_plan(db, user_id, project_id)

        if not plans:
            return {"exists": False, "message": "No plan found for this project"}

        return {
            "exists": True,
            "total_steps": len(plans),
            "created_at": plans[0].created_at,
            "updated_at": plans[-1].updated_at,
            "steps": [
                {
                    "step_id": plan.step_id,
                    "text": plan.text,
                    "created_at": plan.created_at,
                }
                for plan in plans
            ],
        }

    def get_project_agent_calls(
        self, db: Session, project_id: uuid.UUID, limit: int = 100
    ) -> List[AgentCall]:
        """Retrieve agent call history for a project"""
        agent_calls = (
            db.query(AgentCall)
            .filter(AgentCall.project_id == project_id)
            .order_by(AgentCall.created_at.desc())
            .limit(limit)
            .all()
        )

        return agent_calls

    def get_agent_call_summary(
        self, db: Session, project_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get a summary of agent calls for a project"""
        agent_calls = self.get_project_agent_calls(db, project_id)

        if not agent_calls:
            return {"exists": False, "message": "No agent calls found for this project"}

        # Calculate some basic statistics
        total_calls = len(agent_calls)
        successful_calls = len(
            [call for call in agent_calls if not call.response.startswith("Error:")]
        )
        failed_calls = total_calls - successful_calls

        # Get recent activity
        recent_calls = agent_calls[:10]  # Last 10 calls

        return {
            "exists": True,
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": (successful_calls / total_calls) * 100
            if total_calls > 0
            else 0,
            "first_call": agent_calls[-1].created_at if agent_calls else None,
            "last_call": agent_calls[0].created_at if agent_calls else None,
            "recent_calls": [
                {
                    "id": str(call.id),
                    "prompt_preview": call.prompt[:100] + "..."
                    if len(call.prompt) > 100
                    else call.prompt,
                    "response_preview": call.response[:100] + "..."
                    if len(call.response) > 100
                    else call.response,
                    "created_at": call.created_at,
                    "is_error": call.response.startswith("Error:"),
                }
                for call in recent_calls
            ],
        }

    def get_agent_call_details(
        self, db: Session, call_id: uuid.UUID
    ) -> Optional[AgentCall]:
        """Get detailed information about a specific agent call"""
        agent_call = db.query(AgentCall).filter(AgentCall.id == call_id).first()
        return agent_call

    def get_project_workflows(
        self, db: Session, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> List[Workflow]:
        """Retrieve all workflows for a project"""

        workflows = (
            db.query(Workflow)
            .filter(Workflow.user_id == user_id, Workflow.project_id == project_id)
            .order_by(Workflow.created_at.desc())
            .all()
        )

        return workflows

    def get_workflow_summary(
        self, db: Session, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get a summary of workflows for a project"""
        workflows = self.get_project_workflows(db, user_id, project_id)

        if not workflows:
            return {"exists": False, "message": "No workflows found for this project"}

        return {
            "exists": True,
            "total_workflows": len(workflows),
            "workflows": [
                {
                    "id": str(wf.id),
                    "name": wf.name,
                    "description": wf.description,
                    "status": wf.status,
                    "version": wf.version,
                    "created_at": wf.created_at,
                    "updated_at": wf.updated_at,
                    "node_count": len(wf.workflow_graph.get("nodes", [])),
                    "edge_count": len(wf.workflow_graph.get("edges", [])),
                    "state_variable_count": len(
                        wf.state_schema.get("state_variables", [])
                    ),
                    "decision_point_count": len(
                        wf.state_schema.get("decision_points", [])
                    ),
                }
                for wf in workflows
            ],
        }

    def get_workflow_by_id(
        self, db: Session, workflow_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Workflow]:
        """Retrieve a specific workflow by ID with user ownership check"""
        workflow = (
            db.query(Workflow)
            .filter(Workflow.id == workflow_id, Workflow.user_id == user_id)
            .first()
        )

        return workflow

    def get_workflow_details(
        self, db: Session, workflow_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Get detailed workflow information including graph structure"""
        workflow = self.get_workflow_by_id(db, workflow_id, user_id)

        if not workflow:
            return None

        return {
            "id": str(workflow.id),
            "name": workflow.name,
            "description": workflow.description,
            "status": workflow.status,
            "version": workflow.version,
            "created_at": workflow.created_at,
            "updated_at": workflow.updated_at,
            "workflow_graph": workflow.workflow_graph,
            "state_schema": workflow.state_schema,
            "decision_points": workflow.decision_points,
            "generation_prompt": workflow.generation_prompt,
            "ai_model_used": workflow.ai_model_used,
            "project_id": str(workflow.project_id),
            "user_id": str(workflow.user_id),
        }
