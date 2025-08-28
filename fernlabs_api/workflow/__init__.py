"""
AI-powered workflow system using pydantic-graph.
"""

from fernlabs_api.workflow.workflow_agent import WorkflowAgent
from fernlabs_api.workflow.nodes import (
    CreatePlan,
    AssessPlan,
    WaitForUserInput,
    EditPlan,
)
from fernlabs_api.workflow.base import (
    WorkflowState,
    WorkflowDependencies,
    PlanResponse,
    PlanDependencies,
)

# For backward compatibility, also export the main classes
__all__ = [
    "WorkflowAgent",
    "CreatePlan",
    "AssessPlan",
    "WaitForUserInput",
    "EditPlan",
    "WorkflowState",
    "WorkflowDependencies",
    "PlanResponse",
    "PlanDependencies",
]
