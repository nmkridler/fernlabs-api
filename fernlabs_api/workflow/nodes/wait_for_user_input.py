"""
WaitForUserInput node for pausing workflow until user provides response.
"""

from dataclasses import dataclass
from typing import Annotated
from pydantic_graph import BaseNode, GraphRunContext, Edge, End

from fernlabs_api.workflow.base import (
    WorkflowState,
    WorkflowDependencies,
    _update_project_status,
    _log_agent_call,
)
from fernlabs_api.workflow.nodes.edit_plan import EditPlan


@dataclass
class WaitForUserInput(BaseNode[WorkflowState, WorkflowDependencies]):
    """Wait for user to provide response to follow-up question"""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDependencies]
    ) -> (
        Annotated["EditPlan", Edge(label="User Responded")]
        | Annotated["End", Edge(label="Waiting for Input")]
    ):
        """This node represents waiting for user input - pauses workflow and returns question"""

        # Check if we have a user response in the state
        if ctx.state.user_response and ctx.state.user_response.strip():
            # Update project status to indicate we're processing the response
            _update_project_status(ctx.deps.db, ctx.state.project_id, "processing")

            # Log that we're proceeding with the user's response
            await _log_agent_call(
                ctx.deps.db,
                ctx.state.project_id,
                "WaitForUserInput: User response received",
                f"Proceeding to EditPlan with user response: {ctx.state.user_response[:100]}...",
            )

            return EditPlan()
        else:
            # No user response yet, pause the workflow and return the question
            # Update project status to indicate we're waiting for input
            _update_project_status(ctx.deps.db, ctx.state.project_id, "needs_input")

            # Return End with the follow-up question to pause the workflow
            # The client will receive this and can provide a response
            return End(
                {
                    "status": "waiting_for_input",
                    "followup_question": ctx.state.followup_question,
                    "message": "Please provide additional information to continue",
                    "workflow_paused": True,
                }
            )
