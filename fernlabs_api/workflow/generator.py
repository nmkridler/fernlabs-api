"""
Standalone AI-powered workflow agent using pydantic_ai
"""

from typing import List, Dict, Any, Optional
from pydantic_ai import Agent, RunContext
from pydantic_ai.providers import BaseProvider
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.google_gla import GoogleGLAProvider

from pydantic import BaseModel, Field
from fernlabs_api.schema.workflow import (
    WorkflowGenerationRequest,
    WorkflowDefinition,
    WorkflowGraph,
    WorkflowNode,
    WorkflowEdge,
    StateVariable,
    DecisionPoint,
)
from fernlabs_api.settings import APISettings
from fernlabs_api.db.model import Plan, Workflow
from sqlalchemy.orm import Session
import uuid


def _provider_factory(provider_name: str, api_key: str) -> BaseProvider:
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
    db: Session


class PlanRequest(BaseModel):
    """Request for plan creation or editing"""

    project_description: str
    project_type: Optional[str] = None
    requirements: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    existing_plan: Optional[str] = None  # For editing existing plans


class PlanResponse(BaseModel):
    """Response containing the created or edited plan"""

    plan: str
    summary: str
    key_phases: List[str]
    estimated_duration: str


class NodeRelationshipRequest(BaseModel):
    """Request to translate a plan into nodes and relationships"""

    plan: str
    workflow_type: str = "general"  # e.g., "data_pipeline", "ml_training", "web_app"


class NodeRelationshipResponse(BaseModel):
    """Response containing nodes and their relationships"""

    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    state_variables: List[StateVariable]
    decision_points: List[DecisionPoint]


class MermaidRequest(BaseModel):
    """Request to generate a mermaid chart from nodes and relationships"""

    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    chart_type: str = "flowchart"  # flowchart, graph, sequence


class MermaidResponse(BaseModel):
    """Response containing the mermaid chart definition"""

    mermaid_code: str
    chart_type: str
    description: str


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
                "Always provide comprehensive, actionable outputs."
            ),
            provider=_provider_factory(
                settings.api_model_provider, settings.api_model_key
            ),
        )

        # Register tools with the agent
        self._register_tools()

    def _register_tools(self):
        """Register all tools with the agent"""

        @self.agent.tool
        async def create_plan(
            ctx: RunContext[PlanDependencies],
            project_description: str,
            project_type: Optional[str] = None,
            requirements: Optional[List[str]] = None,
            constraints: Optional[List[str]] = None,
        ) -> PlanResponse:
            """Create a comprehensive project plan from description and requirements"""

            # Build the prompt with chat history context
            chat_context = "\n".join(
                [
                    f"{msg['role'].title()}: {msg['content']}"
                    for msg in ctx.deps.chat_history
                ]
            )

            prompt = f"""
            Based on the following conversation history and project requirements, create a comprehensive project plan:

            Conversation History:
            {chat_context}

            Project Description: {project_description}
            Project Type: {project_type or "general"}
            {f"Requirements: {', '.join(requirements)}" if requirements else ""}
            {f"Constraints: {', '.join(constraints)}" if constraints else ""}

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
            result = await self.agent.run(prompt, deps=ctx.deps)

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

            return result.output

        @self.agent.tool
        async def edit_plan(
            ctx: RunContext[PlanDependencies],
            project_description: str,
            existing_plan: str,
            project_type: Optional[str] = None,
            requirements: Optional[List[str]] = None,
            constraints: Optional[List[str]] = None,
        ) -> PlanResponse:
            """Edit and improve an existing project plan"""

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

            Project Context:
            Project Description: {project_description}
            Project Type: {project_type or "general"}
            {f"Requirements: {', '.join(requirements)}" if requirements else ""}
            {f"Constraints: {', '.join(constraints)}" if constraints else ""}

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
            result = await self.agent.run(prompt, deps=ctx.deps)

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

            return result.output

        @self.agent.tool
        async def translate_to_nodes(
            ctx: RunContext[PlanDependencies],
            plan: str,
            workflow_type: str = "general",
        ) -> NodeRelationshipResponse:
            """Translate a project plan into structured workflow nodes and relationships"""

            # Build the prompt for workflow translation
            prompt = f"""
            Convert the following project plan into a structured workflow with nodes and relationships:

            Plan:
            {plan}

            Workflow Type: {workflow_type}

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
            - Suitable for the specified workflow type: {workflow_type}

            Return a complete workflow structure with all components properly defined.
            """

            # Use the agent to generate the workflow structure
            result = await self.agent.run(prompt, deps=ctx.deps)

            # Store the workflow in the database
            await self._store_workflow_in_db(
                ctx.deps.db,
                ctx.deps.user_id,
                ctx.deps.project_id,
                result.output,
                workflow_type,
                plan,
            )

            return result.output

        @self.agent.tool
        async def generate_mermaid_chart(
            ctx: RunContext[PlanDependencies],
            nodes: List[WorkflowNode],
            edges: List[WorkflowEdge],
            chart_type: str = "flowchart",
        ) -> MermaidResponse:
            """Generate a Mermaid chart from workflow nodes and relationships"""

            # This tool will be called by the agent when needed
            # The agent will handle the actual chart generation logic
            pass

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

    async def create_complete_workflow(
        self,
        project_description: str,
        project_type: Optional[str] = None,
        requirements: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a complete workflow from project description to mermaid chart"""

        prompt = f"""
        Create a complete workflow for the following project:

        Project Description: {project_description}
        Project Type: {project_type or "general"}
        {f"Requirements: {', '.join(requirements)}" if requirements else ""}
        {f"Constraints: {', '.join(constraints)}" if constraints else ""}

        Please:
        1. Create a comprehensive project plan using create_plan
        2. Translate that plan into workflow nodes and relationships using translate_to_nodes
        3. Generate a Mermaid chart using generate_mermaid_chart
        4. Return a complete workflow definition

        Use the appropriate tools for each step and ensure the workflow is:
        - Well-structured and executable
        - Clear about task dependencies and flow
        - Suitable for automation
        - Properly visualized with the Mermaid chart
        """

        result = await self.agent.run(prompt)
        return result.output

    async def create_plan_only(
        self,
        project_description: str,
        project_type: Optional[str] = None,
        requirements: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
    ) -> PlanResponse:
        """Create only a project plan"""

        prompt = f"""
        Create a comprehensive project plan for:

        Project Description: {project_description}
        Project Type: {project_type or "general"}
        {f"Requirements: {', '.join(requirements)}" if requirements else ""}
        {f"Constraints: {', '.join(constraints)}" if constraints else ""}

        Use create_plan to generate a detailed, actionable plan.
        """

        result = await self.agent.run(prompt)
        return result.output

    async def edit_plan_only(
        self,
        project_description: str,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        project_type: Optional[str] = None,
        requirements: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        db: Optional[Session] = None,
    ) -> PlanResponse:
        """Edit only an existing project plan"""

        if not db:
            raise ValueError("Database session is required for editing plans")

        # Get existing plan from database
        existing_plan_text = self._get_existing_plan_text(db, user_id, project_id)

        if not existing_plan_text:
            raise ValueError("No existing plan found for this project")

        # Create dependencies
        deps = PlanDependencies(
            user_id=user_id,
            project_id=project_id,
            chat_history=chat_history or [],
            db=db,
        )

        prompt = f"""
        Review and improve this existing project plan:

        Original Plan: {existing_plan_text}
        Project Description: {project_description}
        Project Type: {project_type or "general"}
        {f"Requirements: {', '.join(requirements)}" if requirements else ""}
        {f"Constraints: {', '.join(constraints)}" if constraints else ""}

        Use edit_plan to improve the plan while maintaining its core structure.
        """

        result = await self.agent.run(prompt, deps=deps)
        return result.output

    async def generate_workflow_structure(
        self,
        plan: str,
        workflow_type: str = "general",
        user_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        db: Optional[Session] = None,
    ) -> NodeRelationshipResponse:
        """Generate workflow structure from an existing plan"""

        if not all([user_id, project_id, db]):
            raise ValueError(
                "user_id, project_id, and db are required for workflow generation"
            )

        # Create dependencies
        deps = PlanDependencies(
            user_id=user_id,
            project_id=project_id,
            chat_history=[],  # Empty for now, could be enhanced later
            db=db,
        )

        prompt = f"""
        Convert this project plan into a structured workflow:

        Plan: {plan}
        Workflow Type: {workflow_type}

        Use translate_to_nodes to create workflow nodes, edges, state variables, and decision points.
        """

        result = await self.agent.run(prompt, deps=deps)
        return result.output

    async def create_mermaid_visualization(
        self,
        nodes: List[WorkflowNode],
        edges: List[WorkflowEdge],
        chart_type: str = "flowchart",
    ) -> MermaidResponse:
        """Create a Mermaid chart from workflow structure"""

        prompt = f"""
        Generate a Mermaid chart for this workflow:

        Nodes: {[node.model_dump() for node in nodes]}
        Edges: {[edge.model_dump() for edge in edges]}
        Chart Type: {chart_type}

        Use generate_mermaid_chart to create a clear, readable visualization.
        """

        result = await self.agent.run(prompt)
        return result.output

    async def _store_workflow_in_db(
        self,
        db: Session,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        workflow_data: NodeRelationshipResponse,
        workflow_type: str,
        original_plan: str,
    ):
        """Store the generated workflow in the workflows table"""

        # Convert nodes and edges to JSON format for storage
        workflow_graph = {
            "nodes": [node.model_dump() for node in workflow_data.nodes],
            "edges": [edge.model_dump() for edge in workflow_data.edges],
        }

        # Convert state variables to JSON schema format
        state_schema = {
            "state_variables": [
                var.model_dump() for var in workflow_data.state_variables
            ],
            "decision_points": [
                dp.model_dump() for dp in workflow_data.decision_points
            ],
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
        db.commit()

        return workflow

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


# Legacy WorkflowGenerator class for backward compatibility
class WorkflowGenerator:
    """Legacy workflow generator - use WorkflowAgent instead"""

    def __init__(self, settings: APISettings):
        self.agent = WorkflowAgent(settings)

    async def generate_workflow(
        self, request: WorkflowGenerationRequest
    ) -> WorkflowDefinition:
        """Generate a complete workflow definition from user description"""
        result = await self.agent.create_complete_workflow(
            project_description=request.project_description,
            project_type=request.project_type,
            requirements=request.requirements,
            constraints=request.constraints,
        )
        return result["complete_workflow"]
