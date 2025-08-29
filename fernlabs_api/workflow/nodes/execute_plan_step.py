"""
ExecutePlanStep functions-only module. Exposes `run_execute_plan_step`.
Returns a routing marker string "ExecutePlanStep" or "WaitForUserInput",
or a tuple ("End", payload) when execution completes or fails.
"""

from typing import Any, Tuple

from fernlabs_api.workflow.base import (
    _get_next_execution_steps,
    _update_project_status,
    _log_agent_call,
)


async def run_execute_plan_step(ctx: Any) -> Tuple[str, Any] | str:
    """Execute the current plan step and determine the next route or end."""

    if ctx.state.current_step_id is None:
        ctx.state.current_step_id = 1
        ctx.state.execution_path = [1]

    next_steps = _get_next_execution_steps(
        ctx.deps.db, ctx.state.project_id, ctx.state.current_step_id
    )

    if not next_steps:
        _update_project_status(ctx.deps.db, ctx.state.project_id, "completed")
        return ("End", {"status": "completed", "message": "Plan execution completed"})

    next_step = next_steps[0]

    if next_step["connection_type"] == "conditional":
        ctx.state.followup_question = (
            f"Decision required at step {next_step['step_id']}: {next_step['text']}"
        )
        return "WaitForUserInput"

    await _log_agent_call(
        ctx.deps.db,
        ctx.state.project_id,
        f"Executing step {next_step['step_id']}",
        f"Step executed: {next_step['text']}",
    )

    ctx.state.current_step_id = next_step["step_id"]
    ctx.state.execution_path.append(next_step["step_id"])

    if len(ctx.state.execution_path) > 100:
        _update_project_status(ctx.deps.db, ctx.state.project_id, "failed")
        return (
            "End",
            {
                "status": "failed",
                "message": "Execution limit exceeded - possible infinite loop detected",
            },
        )

    return "ExecutePlanStep"
