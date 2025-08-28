"""
Main workflow agent that orchestrates the AI-powered workflow system.
"""

from typing import List, Dict, Any, Optional
import uuid
from sqlalchemy.orm import Session
from pydantic_graph import Graph
from loguru import logger

from fernlabs_api.settings import APISettings
from fernlabs_api.db.model import Plan, Workflow, AgentCall, Project
from fernlabs_api.workflow.nodes import (
    CreatePlan,
    AssessPlan,
    WaitForUserInput,
    EditPlan,
)
from fernlabs_api.workflow.base import WorkflowState, WorkflowDependencies

logger.add("async_log.log", enqueue=True)

# Create the workflow graph
workflow_graph = Graph(
    nodes=[CreatePlan, AssessPlan, WaitForUserInput, EditPlan], state_type=WorkflowState
)


class WorkflowAgent:
    """Refactored workflow agent using pydantic-graph"""

    def __init__(self, settings: APISettings):
        self.settings = settings
        self.graph = workflow_graph

    async def resume_workflow(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        chat_history: List[Dict[str, str]],
        db: Session,
        user_response: str,
    ) -> Dict[str, Any]:
        """Resume a workflow that was waiting for user input"""

        # Initialize workflow state with the user response
        initial_state = WorkflowState(
            user_id=user_id,
            project_id=project_id,
            chat_history=chat_history,
            db=db,
            user_response=user_response,
        )

        # Initialize dependencies
        deps = WorkflowDependencies(settings=self.settings, db=db)

        try:
            # Start from WaitForUserInput since that's where we were waiting
            result = await self.graph.run(
                WaitForUserInput(), state=initial_state, deps=deps
            )

            # Get the mermaid chart from the workflow state
            mermaid_chart = result.state.mermaid_chart if result.state else None

            return {
                "output": result.output,
                "final_state": result.state,
                "history": chat_history,
                "completed": True,
                "mermaid_chart": mermaid_chart,
            }

        except Exception as e:
            logger.error(f"Workflow resumption error: {e}")
            raise e

    async def run_workflow(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        chat_history: List[Dict[str, str]],
        db: Session,
        user_response: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the complete workflow for plan creation and improvement"""

        # Initialize workflow state
        initial_state = WorkflowState(
            user_id=user_id,
            project_id=project_id,
            chat_history=chat_history,
            db=db,
            user_response=user_response,
        )

        # Initialize dependencies
        deps = WorkflowDependencies(settings=self.settings, db=db)

        try:
            # Run the workflow
            result = await self.graph.run(CreatePlan(), state=initial_state, deps=deps)

            # Check if the workflow ended with waiting_for_input status
            if (
                hasattr(result, "output")
                and result.output
                and isinstance(result.output, dict)
                and result.output.get("status") == "waiting_for_input"
            ):
                return {
                    "output": None,
                    "final_state": result.state,
                    "history": chat_history,
                    "completed": False,
                    "waiting_for_input": True,
                    "followup_question": result.output.get("followup_question"),
                    "message": result.output.get("message"),
                    "workflow_paused": True,
                }

            # Get the mermaid chart from the workflow state
            mermaid_chart = result.state.mermaid_chart if result.state else None

            return {
                "output": result.output,
                "final_state": result.state,
                "history": chat_history,
                "completed": True,
                "mermaid_chart": mermaid_chart,
            }

        except Exception as e:
            logger.error(f"Workflow execution error: {e}")

            # Check if the error is due to waiting for user input
            if "WaitForUserInput" in str(e) or "user input" in str(e).lower():
                # Workflow is waiting for user input
                return {
                    "output": None,
                    "final_state": initial_state,
                    "history": [],
                    "completed": False,
                    "waiting_for_input": True,
                    "followup_question": initial_state.followup_question,
                    "message": "Workflow is waiting for user input to continue",
                }
            else:
                # Some other error occurred
                raise e

    def generate_mermaid_diagram(
        self,
        db: Session = None,
        user_id: uuid.UUID = None,
        project_id: uuid.UUID = None,
    ) -> str:
        """Generate a Mermaid diagram of the workflow or project plan"""
        # If we have database access and project info, generate plan-based diagram
        if db and user_id and project_id:
            plans = self.get_project_plan(db, user_id, project_id)
            if plans and len(plans) > 0:
                return self._generate_plan_mermaid_diagram(plans)

        # Fallback to workflow structure diagram
        return self.graph.mermaid_code(start_node=CreatePlan)

    def _generate_plan_mermaid_diagram(self, plans: List[Plan]) -> str:
        """Generate a Mermaid diagram from the actual project plan steps"""
        if not plans:
            return "flowchart TD\n    A[No Plan Available]"

        mermaid_lines = ["flowchart TD"]

        # Add start node
        mermaid_lines.append("    Start([Start])")

        # Add plan steps
        for i, plan in enumerate(plans):
            step_id = plan.step_id
            step_text = plan.text.strip()

            # Clean up step text for mermaid (remove special characters)
            clean_text = step_text.replace('"', "'").replace(":", " -")
            if len(clean_text) > 50:
                clean_text = clean_text[:47] + "..."

            mermaid_lines.append(f"    Step{step_id}[{step_id}. {clean_text}]")

            # Add connections
            if i == 0:
                mermaid_lines.append("    Start --> Step1")
            else:
                mermaid_lines.append(f"    Step{i} --> Step{step_id}")

        # Add end node
        mermaid_lines.append("    End([End])")
        mermaid_lines.append(f"    Step{len(plans)} --> End")

        return "\n".join(mermaid_lines)

    # Utility methods for backward compatibility
    def get_project_plan(
        self, db: Session, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> Optional[List[Plan]]:
        """Retrieve the complete plan for a project"""
        plans = (
            db.query(Plan)
            .filter(Plan.user_id == user_id, Plan.project_id == project_id)
            .order_by(Plan.step_id)
            .all()
        )

        return plans if plans else None

    def get_plan_summary(
        self, db: Session, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get a summary of the plan including step count and creation info"""
        plans = self.get_project_plan(db, user_id, project_id)

        if not plans:
            return {"exists": False, "message": "No plan found for this project"}

        return {
            "exists": True,
            "total_steps": len(plans),
            "created_at": plans[0].created_at,
            "updated_at": plans[-1].updated_at,
            "steps": [
                {
                    "step_id": plan.step_id,
                    "text": plan.text,
                    "created_at": plan.created_at,
                }
                for plan in plans
            ],
        }

    def get_project_agent_calls(
        self, db: Session, project_id: uuid.UUID, limit: int = 100
    ) -> List[AgentCall]:
        """Retrieve agent call history for a project"""
        agent_calls = (
            db.query(AgentCall)
            .filter(AgentCall.project_id == project_id)
            .order_by(AgentCall.created_at.desc())
            .limit(limit)
            .all()
        )

        return agent_calls

    def get_agent_call_summary(
        self, db: Session, project_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get a summary of agent calls for a project"""
        agent_calls = self.get_project_agent_calls(db, project_id)

        if not agent_calls:
            return {"exists": False, "message": "No agent calls found for this project"}

        # Calculate some basic statistics
        total_calls = len(agent_calls)
        successful_calls = len(
            [call for call in agent_calls if not call.response.startswith("Error:")]
        )
        failed_calls = total_calls - successful_calls

        # Get recent activity
        recent_calls = agent_calls[:10]  # Last 10 calls

        return {
            "exists": True,
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": (successful_calls / total_calls) * 100
            if total_calls > 0
            else 0,
            "first_call": agent_calls[-1].created_at if agent_calls else None,
            "last_call": agent_calls[0].created_at if agent_calls else None,
            "recent_calls": [
                {
                    "id": str(call.id),
                    "prompt_preview": call.prompt[:100] + "..."
                    if len(call.prompt) > 100
                    else call.prompt,
                    "response_preview": call.response[:100] + "..."
                    if len(call.response) > 100
                    else call.response,
                    "created_at": call.created_at,
                    "is_error": call.response.startswith("Error:"),
                }
                for call in recent_calls
            ],
        }

    def get_agent_call_details(
        self, db: Session, call_id: uuid.UUID
    ) -> Optional[AgentCall]:
        """Get detailed information about a specific agent call"""
        agent_call = db.query(AgentCall).filter(AgentCall.id == call_id).first()
        return agent_call

    def get_project_workflows(
        self, db: Session, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> List[Workflow]:
        """Retrieve all workflows for a project"""

        workflows = (
            db.query(Workflow)
            .filter(Workflow.user_id == user_id, Workflow.project_id == project_id)
            .order_by(Workflow.created_at.desc())
            .all()
        )

        return workflows

    def get_workflow_summary(
        self, db: Session, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get a summary of workflows for a project"""
        workflows = self.get_project_workflows(db, user_id, project_id)

        if not workflows:
            return {"exists": False, "message": "No workflows found for this project"}

        return {
            "exists": True,
            "total_workflows": len(workflows),
            "workflows": [
                {
                    "id": str(wf.id),
                    "name": wf.name,
                    "description": wf.description,
                    "status": wf.status,
                    "version": wf.version,
                    "created_at": wf.created_at,
                    "updated_at": wf.updated_at,
                    "node_count": len(wf.workflow_graph.get("nodes", [])),
                    "edge_count": len(wf.workflow_graph.get("edges", [])),
                    "state_variable_count": len(
                        wf.state_schema.get("state_variables", [])
                    ),
                    "decision_point_count": len(
                        wf.state_schema.get("decision_points", [])
                    ),
                }
                for wf in workflows
            ],
        }

    def get_workflow_by_id(
        self, db: Session, workflow_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Workflow]:
        """Retrieve a specific workflow by ID with user ownership check"""
        workflow = (
            db.query(Workflow)
            .filter(Workflow.id == workflow_id, Workflow.user_id == user_id)
            .first()
        )

        return workflow

    def get_workflow_details(
        self, db: Session, workflow_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Get detailed workflow information including graph structure"""
        workflow = self.get_workflow_by_id(db, workflow_id, user_id)

        if not workflow:
            return None

        return {
            "id": str(workflow.id),
            "name": workflow.name,
            "description": workflow.description,
            "status": workflow.status,
            "version": workflow.version,
            "created_at": workflow.created_at,
            "updated_at": workflow.updated_at,
            "workflow_graph": workflow.workflow_graph,
            "state_schema": workflow.state_schema,
            "decision_points": workflow.decision_points,
            "generation_prompt": workflow.generation_prompt,
            "ai_model_used": workflow.ai_model_used,
            "project_id": str(workflow.project_id),
            "user_id": str(workflow.user_id),
        }
