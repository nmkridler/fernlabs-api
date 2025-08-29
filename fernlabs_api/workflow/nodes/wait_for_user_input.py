"""
WaitForUserInput functions-only module. Exposes `run_wait_for_user_input`.
Returns a routing marker string "EditPlan" or a tuple ("End", payload) for pause.
"""

from typing import Any, Tuple

from fernlabs_api.workflow.base import _update_project_status, _log_agent_call


async def run_wait_for_user_input(ctx: Any) -> Tuple[str, Any] | str:
    """Pause and await user input. Returns either "EditPlan" or ("End", payload)."""

    if ctx.state.user_response and ctx.state.user_response.strip():
        _update_project_status(ctx.deps.db, ctx.state.project_id, "processing")

        await _log_agent_call(
            ctx.deps.db,
            ctx.state.project_id,
            "WaitForUserInput: User response received",
            f"Proceeding to EditPlan with user response: {ctx.state.user_response[:100]}...",
        )

        return "EditPlan"
    else:
        _update_project_status(ctx.deps.db, ctx.state.project_id, "needs_input")
        return (
            "End",
            {
                "status": "waiting_for_input",
                "followup_question": ctx.state.followup_question,
                "message": "Please provide additional information to continue",
                "workflow_paused": True,
            },
        )
