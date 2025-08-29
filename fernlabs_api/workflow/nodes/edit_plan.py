"""
EditPlan functions-only module. Exposes `run_edit_plan`.
Returns a routing marker string: "AssessPlan".
"""

import uuid
from typing import Any

from pydantic_ai import Agent

from fernlabs_api.workflow.base import (
    PlanResponse,
    _parse_plan_into_steps,
    _parse_connections_from_plan,
    _generate_plan_mermaid_chart_with_connections,
    _save_mermaid_chart_to_project,
    _save_plan_connections_to_db,
    _update_project_status,
    _log_agent_call,
    _model_factory,
)
from fernlabs_api.db.model import Plan


async def run_edit_plan(ctx: Any) -> str:
    """Edit and improve an existing plan. Returns routing marker "AssessPlan"."""

    _update_project_status(ctx.deps.db, ctx.state.project_id, "loading")

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

    chat_context = "\n".join(
        [f"{msg['role'].title()}: {msg['content']}" for msg in ctx.state.chat_history]
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

    result = await agent.run(prompt)
    improved_plan = result.output

    await _log_agent_call(ctx.deps.db, ctx.state.project_id, prompt, str(improved_plan))

    improved_plan_steps = _parse_plan_into_steps(improved_plan.plan)

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

    improved_plan_connections = _parse_connections_from_plan(improved_plan.plan)

    ctx.state.current_plan = improved_plan.plan
    ctx.state.mermaid_chart = _generate_plan_mermaid_chart_with_connections(
        improved_plan_steps, improved_plan_connections
    )
    ctx.state.plan_needs_improvement = False
    ctx.state.followup_question = None
    ctx.state.user_response = None

    _save_plan_connections_to_db(
        ctx.deps.db,
        ctx.state.project_id,
        improved_plan_connections,
        improved_plan_steps,
    )

    _save_mermaid_chart_to_project(
        ctx.deps.db, ctx.state.project_id, ctx.state.mermaid_chart
    )

    return "AssessPlan"
