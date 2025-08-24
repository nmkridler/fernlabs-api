"""
Standalone AI-powered workflow agent using pydantic_ai
"""

from typing import List, Dict, Any, Optional
import uuid
import asyncio

from pydantic_ai import Agent, RunContext
from pydantic_ai.providers import Provider
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from pydantic import BaseModel


from fernlabs_api.settings import APISettings
from fernlabs_api.db.model import Plan, Workflow, AgentCall, Project
from sqlalchemy.orm import Session


def _provider_factory(provider_name: str, api_key: str) -> Provider:
    """Create a provider based on the model name"""
    if provider_name == "mistral":
        return MistralProvider(api_key=api_key)
    elif provider_name == "openai":
        return OpenAIProvider(api_key=api_key)
    elif provider_name == "google-gla":
        return GoogleGLAProvider(api_key=api_key)

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
    summary: str
    key_phases: List[str]
    estimated_duration: str


class WorkflowAgent:
    """Standalone AI agent for workflow planning and visualization"""

    def __init__(self, settings: APISettings):
        self.settings = settings

        # Initialize the main agent with all tools
        self.agent = Agent(
            settings.api_model_name,
            deps_type=PlanDependencies,
            output_type=PlanResponse,
            system_prompt=(
                "You are an expert workflow designer and project planner. "
                "You can create project plans, translate them into workflow structures, "
                "and generate Mermaid charts for visualization. "
                "Always provide comprehensive, actionable outputs. "
                "IMPORTANT: When working with existing plans, use the assess_plan_and_ask_followup "
                "tool to analyze the plan and ask the most important follow-up question to improve it. "
                "This helps ensure plans are continuously refined and enhanced."
            ),
            provider=_provider_factory(
                settings.api_model_provider, settings.api_model_key
            ),
        )

        # Register tools with the agent
        self._register_tools()

    async def _log_agent_call(
        self, db: Session, project_id: uuid.UUID, prompt: str, response: str
    ):
        """Log an agent call and response to the database"""
        agent_call = AgentCall(
            project_id=project_id,
            prompt=prompt,
            response=response,
        )
        db.add(agent_call)
        db.commit()

    async def _run_agent_with_logging(self, prompt: str, deps: PlanDependencies) -> Any:
        """Run the agent with automatic logging of calls and responses"""
        try:
            # Run the agent
            result = await self.agent.run(prompt, deps=deps)

            await asyncio.sleep(1)

            # Log the call and response
            response_text = (
                str(result.output) if hasattr(result, "output") else str(result)
            )
            await self._log_agent_call(deps.db, deps.project_id, prompt, response_text)

            return result
        except Exception as e:
            # Log failed calls as well
            error_response = f"Error: {str(e)}"
            await self._log_agent_call(deps.db, deps.project_id, prompt, error_response)
            raise

    def _update_project_status(self, db: Session, project_id: uuid.UUID, status: str):
        """Update the project status in the database"""
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = status
            db.commit()

    def _generate_mermaid_chart(self, workflow_data: Dict[str, Any]) -> str:
        """Convert workflow data into a Mermaid flowchart"""

        try:
            nodes = workflow_data.get("nodes", [])
            edges = workflow_data.get("edges", [])

            if not nodes:
                return "flowchart TD\n    A[No nodes found] --> B[Please check workflow data]"

            # Start building the Mermaid chart
            mermaid_lines = ["flowchart TD"]

            # Add nodes
            for node in nodes:
                node_id = node.get("id", "unknown")
                node_name = node.get("name", "Unnamed Node")
                node_type = node.get("type", "task")

                # Format node based on type
                if node_type == "decision":
                    mermaid_lines.append(f"    {node_id}{{ {node_name} }}")
                elif node_type == "start":
                    mermaid_lines.append(f"    {node_id}([ {node_name} ])")
                elif node_type == "end":
                    mermaid_lines.append(f"    {node_id}([ {node_name} ])")
                else:
                    mermaid_lines.append(f"    {node_id}[ {node_name} ]")

            # Add edges
            for edge in edges:
                source = edge.get("source", "unknown")
                target = edge.get("target", "unknown")
                label = edge.get("label", "")

                if label:
                    mermaid_lines.append(f"    {source} -->|{label}| {target}")
                else:
                    mermaid_lines.append(f"    {source} --> {target}")

            return "\n".join(mermaid_lines)

        except Exception as e:
            # Fallback to a simple error chart
            return f"""flowchart TD
    A[Error generating chart] --> B[Error: {str(e)}]
    B --> C[Please check workflow data format]"""

    async def _generate_workflow_from_plan(
        self, ctx: RunContext[PlanDependencies], plan_text: str
    ):
        """Generate workflow structure from a plan and store it in the database"""

        workflow_prompt = f"""
        Convert the following project plan into a structured workflow with nodes and relationships:

        Plan:
        {plan_text}

        Create a comprehensive workflow that includes:

        1. **Workflow Nodes**: Each representing a specific task, decision point, or control flow element
           - Each node should have a clear purpose and responsibility
           - Include input/output specifications
           - Consider error handling and success/failure criteria

        2. **State Variables**: Track progress and data throughout the workflow
           - Data being processed or transformed
           - Progress indicators and status flags
           - Configuration parameters and settings
           - Results and outputs from each step

        3. **Decision Points**: Where the workflow can branch based on conditions
           - Business logic decisions
           - Error handling branches
           - Conditional processing paths
           - Quality gates and validation checkpoints

        4. **Edges**: Show the logical flow between nodes
           - Sequential task dependencies
           - Conditional branching paths
           - Error handling flows
           - Parallel execution paths where applicable

        The workflow should be:
        - Executable and automatable
        - Well-structured with clear entry/exit points
        - Flexible enough to handle variations in data and conditions
        - Properly documented for implementation

        Return a complete workflow structure with all components properly defined.
        """

        # Generate workflow structure
        workflow_result = await self._run_agent_with_logging(workflow_prompt, ctx.deps)

        # Generate Mermaid chart from the workflow
        mermaid_chart = self._generate_mermaid_chart(workflow_result.output)

        # Store the workflow in the database
        await self._store_workflow_in_db(
            ctx.deps.db,
            ctx.deps.user_id,
            ctx.deps.project_id,
            workflow_result.output,
            "general",
            plan_text,
            mermaid_chart,
        )

    def _register_tools(self):
        """Register all tools with the agent"""

        @self.agent.tool
        async def assess_plan_and_ask_followup(
            ctx: RunContext[PlanDependencies],
            existing_plan: str,
        ) -> Dict[str, Any]:
            """Assess an existing plan and ask a follow-up question to improve it"""

            # Build the prompt to analyze the existing plan and identify areas for improvement
            chat_context = "\n".join(
                [
                    f"{msg['role'].title()}: {msg['content']}"
                    for msg in ctx.deps.chat_history
                ]
            )

            prompt = f"""
            Analyze the following existing plan and conversation history to identify the most important follow-up question:

            Existing Plan:
            {existing_plan}

            Conversation History:
            {chat_context}

            Based on this analysis, please:

            1. **Assess the Plan**: What aspects are well-defined and what could be improved?
            2. **Identify the Most Critical Gap**: What single piece of information would most improve this plan?
            3. **Generate One Follow-up Question**: Ask the most important question to gather missing information
            4. **Explain Why This Question Matters**: Provide a brief rationale for why this question is critical

            Focus on asking about:
            - Missing technical details or specifications
            - Unclear requirements or constraints
            - Resource or timeline considerations
            - Risk factors or dependencies
            - Success criteria or validation methods

            Return a single, focused follow-up question that will most improve the plan.
            """

            # Use the agent to analyze the plan and generate the follow-up question
            result = await self._run_agent_with_logging(prompt, ctx.deps)

            # Return the actual output from the LLM result
            return result.output

        @self.agent.tool
        async def create_plan(
            ctx: RunContext[PlanDependencies],
        ) -> PlanResponse:
            """Create a comprehensive project plan from description and requirements"""

            # Set project status to loading
            self._update_project_status(ctx.deps.db, ctx.deps.project_id, "loading")

            # Build the prompt with chat history context
            chat_context = "\n".join(
                [
                    f"{msg['role'].title()}: {msg['content']}"
                    for msg in ctx.deps.chat_history
                ]
            )

            prompt = f"""
            Based on the following conversation history create a comprehensive project plan:

            Conversation History:
            {chat_context}

            Create a detailed plan that includes:
            1. A clear project overview and objectives
            2. Logical phases with specific deliverables
            3. Key milestones and checkpoints
            4. Resource requirements and dependencies
            5. Risk considerations and mitigation strategies
            6. Estimated timeline and duration

            Make the plan actionable and suitable for workflow automation.
            """

            # Use the agent to generate the plan
            result = await self._run_agent_with_logging(prompt, ctx.deps)

            # Parse the plan into steps and save to database
            plan_text = result.output.plan
            plan_steps = self._parse_plan_into_steps(plan_text)

            # Save each step to the database
            for step_id, step_text in enumerate(plan_steps, 1):
                plan_entry = Plan(
                    user_id=ctx.deps.user_id,
                    project_id=ctx.deps.project_id,
                    step_id=step_id,
                    text=step_text,
                )
                ctx.deps.db.add(plan_entry)

            ctx.deps.db.commit()

            # Generate workflow from the plan
            await self._generate_workflow_from_plan(ctx, plan_text)

            # Set project status to completed
            self._update_project_status(ctx.deps.db, ctx.deps.project_id, "completed")

            return result.output

        @self.agent.tool
        async def edit_plan(
            ctx: RunContext[PlanDependencies],
            existing_plan: str,
        ) -> PlanResponse:
            """Edit and improve an existing project plan"""

            # Set project status to loading
            self._update_project_status(ctx.deps.db, ctx.deps.project_id, "loading")

            # Build the prompt with chat history context and existing plan
            chat_context = "\n".join(
                [
                    f"{msg['role'].title()}: {msg['content']}"
                    for msg in ctx.deps.chat_history
                ]
            )

            prompt = f"""
            Review and improve the following existing project plan based on new requirements and context:

            Conversation History:
            {chat_context}

            Original Plan:
            {existing_plan}

            Please analyze the existing plan and:
            1. Identify areas that need improvement or updates
            2. Add missing details or phases based on new requirements
            3. Optimize the workflow structure and flow
            4. Ensure all current requirements are addressed
            5. Update timeline estimates if needed
            6. Maintain the core structure while enhancing clarity and completeness
            7. Address any gaps or inconsistencies

            Return an improved version of the plan that builds upon the existing structure.
            """

            # Use the agent to generate the improved plan
            result = await self._run_agent_with_logging(prompt, ctx.deps)

            # Parse the improved plan into steps
            improved_plan_text = result.output.plan
            improved_plan_steps = self._parse_plan_into_steps(improved_plan_text)

            # First, remove the existing plan entries for this project
            existing_plans = (
                ctx.deps.db.query(Plan)
                .filter(
                    Plan.user_id == ctx.deps.user_id,
                    Plan.project_id == ctx.deps.project_id,
                )
                .all()
            )

            for existing_plan_entry in existing_plans:
                ctx.deps.db.delete(existing_plan_entry)

            # Save the improved plan steps to the database
            for step_id, step_text in enumerate(improved_plan_steps, 1):
                plan_entry = Plan(
                    user_id=ctx.deps.user_id,
                    project_id=ctx.deps.project_id,
                    step_id=step_id,
                    text=step_text,
                )
                ctx.deps.db.add(plan_entry)

            ctx.deps.db.commit()

            # Generate workflow from the improved plan
            await self._generate_workflow_from_plan(ctx, improved_plan_text)

            # Set project status to completed
            self._update_project_status(ctx.deps.db, ctx.deps.project_id, "completed")

            return result.output

    def _parse_plan_into_steps(self, plan_text: str) -> List[str]:
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

    def _get_existing_plan_text(
        self, db: Session, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> str:
        """Retrieve existing plan text from database for a given project"""
        existing_plans = (
            db.query(Plan)
            .filter(Plan.user_id == user_id, Plan.project_id == project_id)
            .order_by(Plan.step_id)
            .all()
        )

        if not existing_plans:
            return ""

        # Reconstruct the plan text from stored steps
        plan_text = "\n\n".join([plan.text for plan in existing_plans])
        return plan_text

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

    async def assess_plan_and_ask_followup(
        self,
        existing_plan: str,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        chat_history: List[Dict[str, str]],
        db: Session,
    ) -> Dict[str, Any]:
        """Assess an existing plan and ask a follow-up question to improve it"""

        # Create dependencies
        deps = PlanDependencies(
            user_id=user_id,
            project_id=project_id,
            chat_history=chat_history,
            db=db,
        )

        prompt = f"""
        Assess this existing plan and identify the most important follow-up question to improve it.
        Use the assess_plan_and_ask_followup tool with the existing plan: {existing_plan}
        """

        result = await self._run_agent_with_logging(prompt, deps)
        return result.output

    async def _store_workflow_in_db(
        self,
        db: Session,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        workflow_data: Dict[str, Any],
        workflow_type: str,
        original_plan: str,
        mermaid_chart: str,
    ):
        """Store the generated workflow in the workflows table"""

        # Convert nodes and edges to JSON format for storage
        workflow_graph = {
            "nodes": workflow_data.get("nodes", []),
            "edges": workflow_data.get("edges", []),
        }

        # Convert state variables to JSON schema format
        state_schema = {
            "state_variables": workflow_data.get("state_variables", []),
            "decision_points": workflow_data.get("decision_points", []),
        }

        # Create workflow name from project context
        workflow_name = f"Generated Workflow - {workflow_type.title()}"
        workflow_description = (
            f"AI-generated workflow from plan for {workflow_type} project"
        )

        # Create and save the workflow
        workflow = Workflow(
            project_id=project_id,
            user_id=user_id,
            name=workflow_name,
            description=workflow_description,
            workflow_graph=workflow_graph,
            state_schema=state_schema,
            decision_points=state_schema["decision_points"],
            generation_prompt=original_plan,
            ai_model_used=self.settings.api_model_name,
            status="draft",
        )

        db.add(workflow)

        # Update the project's Mermaid chart
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.mermaid_chart = mermaid_chart

        db.commit()

        return workflow

    def generate_mermaid_from_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """Generate a Mermaid chart from workflow data"""
        return self._generate_mermaid_chart(workflow_data)

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
