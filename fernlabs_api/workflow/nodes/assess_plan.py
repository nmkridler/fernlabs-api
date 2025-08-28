"""
AssessPlan node for evaluating plan quality and determining if follow-up is needed.
"""

from dataclasses import dataclass
from typing import Annotated
from pydantic_ai import Agent
from pydantic_graph import BaseNode, GraphRunContext, Edge, End

from fernlabs_api.workflow.base import (
    WorkflowState,
    WorkflowDependencies,
    PlanResponse,
    _update_project_status,
    _log_agent_call,
    _model_factory,
)
from fernlabs_api.workflow.nodes.wait_for_user_input import WaitForUserInput


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
        await _log_agent_call(ctx.deps.db, ctx.state.project_id, prompt, assessment)

        # Check if plan needs improvement
        if "PLAN_COMPLETE" in assessment.upper():
            # Plan is complete, end the workflow
            ctx.state.final_plan = PlanResponse(
                plan=ctx.state.current_plan,
                mermaid_chart=ctx.state.mermaid_chart,
            )
            _update_project_status(ctx.deps.db, ctx.state.project_id, "completed")
            return End(ctx.state.final_plan)
        else:
            # Plan needs improvement, store follow-up question and wait for user input
            ctx.state.plan_needs_improvement = True
            ctx.state.followup_question = assessment

            return WaitForUserInput()
