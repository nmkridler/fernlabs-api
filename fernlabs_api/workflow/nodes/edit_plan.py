"""
EditPlan node for improving existing plans based on user feedback.
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
class EditPlan(BaseNode[WorkflowState, WorkflowDependencies]):
    """Edit and improve the existing plan based on user response"""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDependencies]
    ) -> Annotated["AssessPlan", Edge(label="Plan Updated")]:
        """Edit and improve the existing project plan based on user feedback"""

        # Set project status to loading
        _update_project_status(ctx.deps.db, ctx.state.project_id, "loading")

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
        await _log_agent_call(
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

        return AssessPlan()
