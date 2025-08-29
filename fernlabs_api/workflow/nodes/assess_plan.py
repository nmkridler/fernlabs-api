"""
AssessPlan functions-only module. Exposes `run_assess_plan`.
Returns a routing marker string "WaitForUserInput" or a tuple ("End", payload).
"""

from typing import Any, Tuple

from pydantic_ai import Agent

from fernlabs_api.workflow.base import (
    PlanResponse,
    _update_project_status,
    _log_agent_call,
    _model_factory,
)


async def run_assess_plan(ctx: Any) -> Tuple[str, Any] | str:
    """Assess the plan and determine if improvements are needed.

    Returns either ("End", PlanResponse) when complete, or "WaitForUserInput".
    """

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

    chat_context = "\n".join(
        [f"{msg['role'].title()}: {msg['content']}" for msg in ctx.state.chat_history]
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

    result = await agent.run(prompt)
    assessment = result.output

    await _log_agent_call(ctx.deps.db, ctx.state.project_id, prompt, assessment)

    if "PLAN_COMPLETE" in assessment.upper():
        ctx.state.final_plan = PlanResponse(
            plan=ctx.state.current_plan,
            mermaid_chart=ctx.state.mermaid_chart,
        )
        _update_project_status(ctx.deps.db, ctx.state.project_id, "completed")
        return ("End", ctx.state.final_plan)
    else:
        ctx.state.plan_needs_improvement = True
        ctx.state.followup_question = assessment
        return "WaitForUserInput"
