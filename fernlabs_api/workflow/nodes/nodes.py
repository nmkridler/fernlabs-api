"""
Centralized node class definitions for the workflow.
Each class delegates to a function implemented in its corresponding module
under this folder (functions-only modules).
"""

from dataclasses import dataclass
from typing import Annotated, Union, Tuple, Any

from pydantic_graph import BaseNode, GraphRunContext, Edge, End

from fernlabs_api.workflow.base import WorkflowState, WorkflowDependencies

# Import per-node run functions (functions-only modules)
from .create_plan import run_create_plan
from .assess_plan import run_assess_plan
from .wait_for_user_input import run_wait_for_user_input
from .edit_plan import run_edit_plan
from .execute_plan_step import run_execute_plan_step


@dataclass
class CreatePlan(BaseNode[WorkflowState, WorkflowDependencies]):
    """Create initial project plan from conversation history"""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDependencies]
    ) -> (
        Annotated["AssessPlan", Edge(label="Plan Created - Needs Review")]
        | Annotated["ExecutePlanStep", Edge(label="Plan Created - Ready to Execute")]
    ):
        result = await run_create_plan(ctx)
        if isinstance(result, str):
            if result == "AssessPlan":
                return AssessPlan()
            if result == "ExecutePlanStep":
                return ExecutePlanStep()
        raise RuntimeError(f"Unexpected routing result for CreatePlan: {result!r}")


@dataclass
class AssessPlan(BaseNode[WorkflowState, WorkflowDependencies]):
    """Assess the created plan and determine if follow-up questions are needed"""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDependencies]
    ) -> (
        Annotated["WaitForUserInput", Edge(label="Needs Followup")]
        | Annotated["End", Edge(label="Plan Complete")]
    ):
        result: Tuple[str, Any] | str = await run_assess_plan(ctx)
        if isinstance(result, tuple) and result and result[0] == "End":
            return End(result[1])
        if isinstance(result, str) and result == "WaitForUserInput":
            return WaitForUserInput()
        raise RuntimeError(f"Unexpected routing result for AssessPlan: {result!r}")


@dataclass
class WaitForUserInput(BaseNode[WorkflowState, WorkflowDependencies]):
    """Wait for user to provide response to follow-up question"""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDependencies]
    ) -> (
        Annotated["EditPlan", Edge(label="User Responded")]
        | Annotated["End", Edge(label="Waiting for Input")]
    ):
        result: Tuple[str, Any] | str = await run_wait_for_user_input(ctx)
        if isinstance(result, tuple) and result and result[0] == "End":
            return End(result[1])
        if isinstance(result, str) and result == "EditPlan":
            return EditPlan()
        raise RuntimeError(
            f"Unexpected routing result for WaitForUserInput: {result!r}"
        )


@dataclass
class EditPlan(BaseNode[WorkflowState, WorkflowDependencies]):
    """Edit and improve the existing plan based on user feedback"""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDependencies]
    ) -> Annotated["AssessPlan", Edge(label="Plan Updated")]:
        result = await run_edit_plan(ctx)
        if isinstance(result, str) and result == "AssessPlan":
            return AssessPlan()
        raise RuntimeError(f"Unexpected routing result for EditPlan: {result!r}")


@dataclass
class ExecutePlanStep(BaseNode[WorkflowState, WorkflowDependencies]):
    """Execute a plan step and route to the next step based on connections"""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDependencies]
    ) -> Union[
        Annotated["ExecutePlanStep", Edge(label="Continue Execution")],
        Annotated["WaitForUserInput", Edge(label="Needs Input")],
        Annotated["End", Edge(label="Execution Complete")],
    ]:
        result: Tuple[str, Any] | str = await run_execute_plan_step(ctx)
        if isinstance(result, tuple) and result and result[0] == "End":
            return End(result[1])
        if isinstance(result, str):
            if result == "ExecutePlanStep":
                return ExecutePlanStep()
            if result == "WaitForUserInput":
                return WaitForUserInput()
        raise RuntimeError(
            f"Unexpected routing result for ExecutePlanStep: {result!r}"
        )


__all__ = [
    "CreatePlan",
    "AssessPlan",
    "WaitForUserInput",
    "EditPlan",
    "ExecutePlanStep",
]
