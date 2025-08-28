"""
Standalone AI-powered workflow agent using pydantic-graph

This module maintains backward compatibility by importing from the refactored structure.
"""

# Import from the new refactored structure
from .workflow_agent import WorkflowAgent
from .nodes import CreatePlan, AssessPlan, WaitForUserInput, EditPlan
from .base import (
    WorkflowState,
    WorkflowDependencies,
    PlanResponse,
    PlanDependencies,
    _parse_plan_into_steps,
    _generate_plan_mermaid_chart,
    _save_mermaid_chart_to_project,
    _update_project_status,
    _log_agent_call,
    _model_factory,
)

# Re-export for backward compatibility
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
    "_parse_plan_into_steps",
    "_generate_plan_mermaid_chart",
    "_save_mermaid_chart_to_project",
    "_update_project_status",
    "_log_agent_call",
    "_model_factory",
]
