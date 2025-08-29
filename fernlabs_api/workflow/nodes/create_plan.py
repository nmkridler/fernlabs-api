"""
CreatePlan functions-only module. Exposes `run_create_plan`.
Returns a routing marker string: "ExecutePlanStep" or "AssessPlan".
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


async def run_create_plan(ctx: Any) -> str:
    """Create a comprehensive project plan from description and requirements.

    Returns routing marker: "ExecutePlanStep" or "AssessPlan".
    """

    _update_project_status(ctx.deps.db, ctx.state.project_id, "loading")

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
            "Identify any connections between steps and include them in the plan."
        ),
    )

    chat_context = "\n".join(
        [f"{msg['role'].title()}: {msg['content']}" for msg in ctx.state.chat_history]
    )

    prompt = f"""
    Based on the following conversation history create a high level project plan:

    Conversation History:
    {chat_context}

    Create a high level plan that outlines the overall flow of the project.
    Be concise, to the point, and only include the most important steps.
    Give each step a succinct title formatted as title: description.
    For example: Load Data: load the data from the csv file.

    The plan should be a numbered list of steps with connections between them.
    The connections should be indicated with arrows.
    """

    result = await agent.run(prompt)
    plan_response = result.output

    ctx.state.current_plan = plan_response.plan

    plan_steps = _parse_plan_into_steps(plan_response.plan)
    plan_connections = _parse_connections_from_plan(plan_response.plan)
    ctx.state.mermaid_chart = _generate_plan_mermaid_chart_with_connections(
        plan_steps, plan_connections
    )

    for step_id, step_text in enumerate(plan_steps, 1):
        plan_entry = Plan(
            id=uuid.uuid4(),
            user_id=ctx.state.user_id,
            project_id=ctx.state.project_id,
            step_id=step_id,
            text=step_text,
        )
        ctx.deps.db.add(plan_entry)

    _save_plan_connections_to_db(
        ctx.deps.db, ctx.state.project_id, plan_connections, plan_steps
    )

    ctx.deps.db.commit()

    _save_mermaid_chart_to_project(
        ctx.deps.db, ctx.state.project_id, ctx.state.mermaid_chart
    )

    await _log_agent_call(ctx.deps.db, ctx.state.project_id, prompt, str(plan_response))

    if len(plan_steps) <= 5 and not any(
        conn["type"] in ["conditional", "loop_back"] for conn in plan_connections
    ):
        return "ExecutePlanStep"
    else:
        return "AssessPlan"
