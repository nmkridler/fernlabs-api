"""
CreatePlan node for generating initial project plans.
"""

import uuid
from dataclasses import dataclass
from typing import Annotated
from pydantic_ai import Agent
from pydantic_graph import BaseNode, GraphRunContext, Edge

from fernlabs_api.workflow.base import (
    WorkflowState,
    WorkflowDependencies,
    PlanResponse,
    _parse_plan_into_steps,
    _generate_plan_mermaid_chart,
    _save_mermaid_chart_to_project,
    _update_project_status,
    _log_agent_call,
    _model_factory,
)
from fernlabs_api.db.model import Plan
from fernlabs_api.workflow.nodes.assess_plan import AssessPlan


@dataclass
class CreatePlan(BaseNode[WorkflowState, WorkflowDependencies]):
    """Create initial project plan from conversation history"""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDependencies]
    ) -> Annotated["AssessPlan", Edge(label="Plan Created")]:
        """Create a comprehensive project plan from description and requirements"""

        # Set project status to loading
        _update_project_status(ctx.deps.db, ctx.state.project_id, "loading")

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
        await _log_agent_call(
            ctx.deps.db, ctx.state.project_id, prompt, str(plan_response)
        )

        return AssessPlan()
