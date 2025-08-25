"""
Projects API routes
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, AsyncIterator
import uuid
from datetime import datetime
import json
from loguru import logger

from fernlabs_api.schema.project import ProjectCreate, ProjectUpdate, ProjectResponse
from fernlabs_api.schema.chat import (
    ChatMessage,
    ChatResponse,
    ChatHistoryResponse,
    ProjectPlanResponse,
)
from fernlabs_api.db import get_db
from fernlabs_api.db.model import Project, User, AgentCall, Plan, Workflow
from fernlabs_api.workflow.generator import WorkflowAgent
from fernlabs_api.settings import APISettings

router = APIRouter()
settings = APISettings()


@router.post("/")
async def create_project(
    request: ProjectCreate,
    db: Session = Depends(get_db),
):
    """Create a new project and stream workflow generation progress"""

    async def stream_workflow_generation() -> AsyncIterator[bytes]:
        try:
            # Create new project with loading status
            project = Project(
                id=uuid.uuid4(),
                user_id=request.user_id,
                name=request.name,
                description=request.description,
                prompt=request.prompt,
                status="loading",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            db.add(project)
            db.commit()
            db.refresh(project)

            # Stream project creation confirmation
            yield (
                json.dumps(
                    {
                        "type": "project_created",
                        "project_id": str(project.id),
                        "status": "loading",
                        "message": "Project created successfully. Starting workflow generation...",
                    }
                ).encode("utf-8")
                + b"\n"
            )

            # Initialize the workflow agent
            agent = WorkflowAgent(settings)

            # Create initial chat history with the user's prompt
            initial_chat_history = [{"role": "user", "content": request.prompt}]

            # Stream agent initialization
            yield (
                json.dumps(
                    {
                        "type": "agent_initialized",
                        "message": "AI agent initialized and analyzing your requirements...",
                    }
                ).encode("utf-8")
                + b"\n"
            )

            # Stream planning phase
            yield (
                json.dumps(
                    {
                        "type": "planning_started",
                        "message": "Creating comprehensive project plan...",
                    }
                ).encode("utf-8")
                + b"\n"
            )

            # Use the new workflow system to create a plan
            try:
                result = await agent.run_workflow(
                    user_id=request.user_id,
                    project_id=project.id,
                    chat_history=initial_chat_history,
                    db=db,
                    user_response=None,
                )

                logger.info(f"Workflow generation result: {result}")

                # Check if the workflow completed successfully
                if result.get("completed", False) and result.get("output"):
                    # Workflow completed successfully
                    yield (
                        json.dumps(
                            {
                                "type": "workflow_completed",
                                "message": "Workflow generation completed successfully!",
                            }
                        ).encode("utf-8")
                        + b"\n"
                    )

                    # Update project status to completed
                    project.status = "completed"
                    db.commit()

                    # Get the updated project with mermaid chart
                    db.refresh(project)

                    # Send the completed project with mermaid chart
                    yield (
                        json.dumps(
                            {
                                "type": "project_completed",
                                "message": "Project completed successfully!",
                                "project": {
                                    "id": str(project.id),
                                    "user_id": str(project.user_id),
                                    "name": project.name,
                                    "description": project.description or "",
                                    "github_repo": project.github_repo or "",
                                    "prompt": project.prompt,
                                    "status": project.status,
                                    "mermaid_chart": project.mermaid_chart,
                                    "created_at": project.created_at.isoformat(),
                                    "updated_at": project.updated_at.isoformat(),
                                },
                            }
                        ).encode("utf-8")
                        + b"\n"
                    )

                elif result.get("waiting_for_input", False):
                    # Workflow needs more input, send follow-up question to client
                    followup_question = result.get(
                        "followup_question", "Please provide additional information"
                    )
                    message = result.get(
                        "message",
                        "The AI agent needs more information to complete your plan.",
                    )

                    yield (
                        json.dumps(
                            {
                                "type": "follow_up_needed",
                                "message": message,
                                "details": followup_question,
                                "action_required": "Please use the chat endpoint to answer the follow-up question.",
                            }
                        ).encode("utf-8")
                        + b"\n"
                    )

                    # Update project status to indicate follow-up is needed
                    project.status = "needs_input"
                    db.commit()

                    yield (
                        json.dumps(
                            {
                                "type": "project_paused",
                                "project": {
                                    "id": str(project.id),
                                    "user_id": str(project.user_id),
                                    "name": project.name,
                                    "description": project.description or "",
                                    "github_repo": project.github_repo or "",
                                    "prompt": project.prompt,
                                    "status": project.status,
                                    "mermaid_chart": project.mermaid_chart,
                                    "created_at": project.created_at.isoformat(),
                                    "updated_at": project.updated_at.isoformat(),
                                },
                                "message": "Project paused. Use the chat endpoint to provide additional information.",
                                "followup_question": followup_question,
                            }
                        ).encode("utf-8")
                        + b"\n"
                    )
                    return

                else:
                    # Workflow needs more input but no specific question
                    yield (
                        json.dumps(
                            {
                                "type": "follow_up_needed",
                                "message": "The AI agent needs more information to complete your plan.",
                                "details": "Please use the chat endpoint to answer follow-up questions.",
                                "action_required": "Please use the chat endpoint to answer follow-up questions.",
                            }
                        ).encode("utf-8")
                        + b"\n"
                    )

                    # Update project status to indicate follow-up is needed
                    project.status = "needs_input"
                    db.commit()

                    yield (
                        json.dumps(
                            {
                                "type": "project_paused",
                                "project": {
                                    "id": str(project.id),
                                    "user_id": str(project.user_id),
                                    "name": project.name,
                                    "description": project.description or "",
                                    "github_repo": project.github_repo or "",
                                    "prompt": project.prompt,
                                    "status": project.status,
                                    "mermaid_chart": project.mermaid_chart,
                                    "created_at": project.created_at.isoformat(),
                                    "updated_at": project.updated_at.isoformat(),
                                },
                                "message": "Project paused. Use the chat endpoint to provide additional information.",
                            }
                        ).encode("utf-8")
                        + b"\n"
                    )
                    return

            except Exception as workflow_error:
                logger.error(f"Workflow execution error: {workflow_error}")
                # If workflow fails, fall back to needs_input status
                project.status = "needs_input"
                db.commit()

                yield (
                    json.dumps(
                        {
                            "type": "follow_up_needed",
                            "message": "Initial plan creation encountered issues. Please provide more details.",
                            "details": str(workflow_error),
                            "action_required": "Please use the chat endpoint to provide additional information.",
                        }
                    ).encode("utf-8")
                    + b"\n"
                )

                yield (
                    json.dumps(
                        {
                            "type": "project_paused",
                            "project": {
                                "id": str(project.id),
                                "user_id": str(project.user_id),
                                "name": project.name,
                                "description": project.description or "",
                                "github_repo": project.github_repo or "",
                                "prompt": project.prompt,
                                "status": project.status,
                                "mermaid_chart": project.mermaid_chart,
                                "created_at": project.created_at.isoformat(),
                                "updated_at": project.updated_at.isoformat(),
                            },
                            "message": "Project paused. Use the chat endpoint to provide additional information.",
                        }
                    ).encode("utf-8")
                    + b"\n"
                )
                return

            # Verify the results were created
            plans = db.query(Plan).filter(Plan.project_id == project.id).all()
            workflows = (
                db.query(Workflow).filter(Workflow.project_id == project.id).all()
            )

            if not plans or not workflows:
                yield (
                    json.dumps(
                        {
                            "type": "warning",
                            "message": "Warning: Agent didn't create plans/workflows for project",
                        }
                    ).encode("utf-8")
                    + b"\n"
                )

            db.commit()

            # Stream final project details
            yield (
                json.dumps(
                    {
                        "type": "project_completed",
                        "project": {
                            "id": str(project.id),
                            "user_id": str(project.user_id),
                            "name": project.name,
                            "description": project.description or "",
                            "github_repo": project.github_repo or "",
                            "prompt": project.prompt,
                            "status": project.status,
                            "mermaid_chart": project.mermaid_chart,
                            "created_at": project.created_at.isoformat(),
                            "updated_at": project.updated_at.isoformat(),
                        },
                        "message": "Project setup complete! Your workflow is ready.",
                    }
                ).encode("utf-8")
                + b"\n"
            )

        except Exception as e:
            # Stream error information
            yield (
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Error during workflow generation: {str(e)}",
                    }
                ).encode("utf-8")
                + b"\n"
            )

            # Update project status to failed if we have a project
            try:
                if "project" in locals():
                    project.status = "failed"
                    db.commit()
            except:
                pass

            raise HTTPException(
                status_code=500, detail=f"Failed to create project: {str(e)}"
            )

    return StreamingResponse(stream_workflow_generation(), media_type="text/plain")


@router.post("/{project_id}/chat", response_model=ChatResponse)
async def chat_with_project(
    project_id: uuid.UUID, message: ChatMessage, db: Session = Depends(get_db)
):
    """Send a message to the project's AI agent and get a response"""
    try:
        # Get the project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get existing chat history from AgentCall
        agent_calls = (
            db.query(AgentCall)
            .filter(AgentCall.project_id == project_id)
            .order_by(AgentCall.created_at)
            .all()
        )

        # Build chat history
        chat_history = []
        for call in agent_calls:
            chat_history.append({"role": "user", "content": call.prompt})
            chat_history.append({"role": "assistant", "content": call.response})

        # Add the new user message
        chat_history.append({"role": "user", "content": message.message})

        # Initialize the workflow agent for interactive responses
        agent = WorkflowAgent(settings)

        # Use the new workflow system to handle the chat
        try:
            # Check if this is a response to a follow-up question
            if project.status == "needs_input" and message.message.strip():
                # This is a response to a follow-up question, resume the workflow
                result = await agent.resume_workflow(
                    user_id=project.user_id,
                    project_id=project.id,
                    chat_history=chat_history,
                    db=db,
                    user_response=message.message,
                )

                if result.get("completed", False):
                    agent_response = "Great! I have enough information now. You can use the resume endpoint to complete your workflow generation."

                    # Update project status to indicate we're ready to complete
                    project.status = "ready_to_complete"
                    db.commit()
                else:
                    agent_response = "I'm still processing your response. Please provide more details if needed."

            else:
                # Regular chat message, run the workflow normally
                result = await agent.run_workflow(
                    user_id=project.user_id,
                    project_id=project.id,
                    chat_history=chat_history,
                    db=db,
                    user_response=message.message,
                )

                # Check if the workflow completed or needs more input
                if result.get("completed", False) and result.get("output"):
                    agent_response = "Great! I have enough information now. You can use the resume endpoint to complete your workflow generation."

                    # Check if we should update project status
                    if project.status == "needs_input":
                        project.status = "ready_to_complete"
                        db.commit()
                else:
                    # Workflow still needs more input
                    agent_response = "I'm still gathering information. Please provide more details about your project requirements."

        except Exception as workflow_error:
            logger.error(f"Workflow execution error in chat: {workflow_error}")
            # Fallback response if workflow fails
            agent_response = f"I'm processing your input: {message.message}. Please continue providing details about your project."

        # Store the conversation in AgentCall
        agent_call = AgentCall(
            id=uuid.uuid4(),
            project_id=project_id,
            prompt=message.message,
            response=agent_response,
        )
        db.add(agent_call)
        db.commit()

        # Check if there's an existing plan
        existing_plan = db.query(Plan).filter(Plan.project_id == project_id).first()

        return ChatResponse(
            response=agent_response,
            project_status=project.status,
            has_plan=existing_plan is not None,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/{project_id}/resume")
async def resume_workflow_generation(
    project_id: uuid.UUID, db: Session = Depends(get_db)
):
    """Resume workflow generation for a project that was paused for follow-up questions"""

    async def stream_workflow_resumption() -> AsyncIterator[bytes]:
        try:
            # Get the project
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            if project.status not in ["needs_input", "ready_to_complete"]:
                yield (
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"Project is not ready for resumption. Current status: {project.status}",
                        }
                    ).encode("utf-8")
                    + b"\n"
                )
                return

            # Stream resumption start
            yield (
                json.dumps(
                    {
                        "type": "resumption_started",
                        "message": "Resuming workflow generation with updated information...",
                    }
                ).encode("utf-8")
                + b"\n"
            )

            # Initialize the workflow agent
            agent = WorkflowAgent(settings)

            # Get updated chat history from AgentCall
            agent_calls = (
                db.query(AgentCall)
                .filter(AgentCall.project_id == project_id)
                .order_by(AgentCall.created_at)
                .all()
            )

            # Build updated chat history
            updated_chat_history = []
            for call in agent_calls:
                updated_chat_history.append({"role": "user", "content": call.prompt})
                updated_chat_history.append(
                    {"role": "assistant", "content": call.response}
                )

            # Stream planning phase
            yield (
                json.dumps(
                    {
                        "type": "planning_resumed",
                        "message": "Creating comprehensive project plan with new information...",
                    }
                ).encode("utf-8")
                + b"\n"
            )

            # Use the new workflow system to complete the plan
            try:
                # Check if we have a user response from previous chat
                if project.status == "ready_to_complete":
                    # We have enough information, complete the workflow
                    result = await agent.run_workflow(
                        user_id=project.user_id,
                        project_id=project.id,
                        chat_history=updated_chat_history,
                        db=db,
                        user_response=None,  # No new user response for resume
                    )
                else:
                    # Try to run the workflow from the beginning
                    result = await agent.run_workflow(
                        user_id=project.user_id,
                        project_id=project.id,
                        chat_history=updated_chat_history,
                        db=db,
                        user_response=None,
                    )

                # Check if the workflow completed successfully
                if result.get("completed", False) and result.get("output"):
                    # Workflow completed successfully
                    yield (
                        json.dumps(
                            {
                                "type": "workflow_completed",
                                "message": "Workflow generation completed successfully!",
                            }
                        ).encode("utf-8")
                        + b"\n"
                    )

                    # Update project status to completed
                    project.status = "completed"
                    db.commit()

                else:
                    # Workflow still needs more input
                    yield (
                        json.dumps(
                            {
                                "type": "follow_up_still_needed",
                                "message": "The AI agent still needs more information to complete your plan.",
                                "details": "Please continue using the chat endpoint to provide more details.",
                                "action_required": "Please continue using the chat endpoint to provide more details.",
                            }
                        ).encode("utf-8")
                        + b"\n"
                    )
                    return

            except Exception as workflow_error:
                logger.error(f"Workflow execution error in resume: {workflow_error}")
                yield (
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"Error during workflow resumption: {str(workflow_error)}",
                        }
                    ).encode("utf-8")
                    + b"\n"
                )
                return

            # Verify the results were created
            plans = db.query(Plan).filter(Plan.project_id == project.id).all()
            workflows = (
                db.query(Workflow).filter(Workflow.project_id == project.id).all()
            )

            if not plans or not workflows:
                yield (
                    json.dumps(
                        {
                            "type": "warning",
                            "message": "Warning: Agent didn't create plans/workflows for project",
                        }
                    ).encode("utf-8")
                    + b"\n"
                )

            # Generate Mermaid chart if not already present
            if not project.mermaid_chart:
                # Use the new workflow agent to generate Mermaid chart from the actual plan
                project.mermaid_chart = agent.generate_mermaid_diagram(
                    db=db, user_id=project.user_id, project_id=project.id
                )

            db.commit()

            # Stream final project details
            yield (
                json.dumps(
                    {
                        "type": "project_completed",
                        "project": {
                            "id": str(project.id),
                            "user_id": str(project.user_id),
                            "name": project.name,
                            "description": project.description or "",
                            "github_repo": project.github_repo or "",
                            "prompt": project.prompt,
                            "status": project.status,
                            "mermaid_chart": project.mermaid_chart,
                            "created_at": project.created_at.isoformat(),
                            "updated_at": project.updated_at.isoformat(),
                        },
                        "message": "Project setup complete! Your workflow is ready.",
                    }
                ).encode("utf-8")
                + b"\n"
            )

        except Exception as e:
            # Stream error information
            yield (
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Error during workflow resumption: {str(e)}",
                    }
                ).encode("utf-8")
                + b"\n"
            )

            # Update project status to failed if we have a project
            try:
                if "project" in locals():
                    project.status = "failed"
                    db.commit()
            except:
                pass

            raise HTTPException(
                status_code=500,
                detail=f"Failed to resume workflow generation: {str(e)}",
            )

    return StreamingResponse(stream_workflow_resumption(), media_type="text/plain")


@router.get("/{project_id}/chat", response_model=ChatHistoryResponse)
async def get_project_chat_history(
    project_id: uuid.UUID, db: Session = Depends(get_db)
):
    """Get the chat history for a project"""
    try:
        # Get the project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get chat history from AgentCall
        agent_calls = (
            db.query(AgentCall)
            .filter(AgentCall.project_id == project_id)
            .order_by(AgentCall.created_at)
            .all()
        )

        # Format chat history
        chat_history = []
        for call in agent_calls:
            chat_history.append(
                {
                    "id": str(call.id),
                    "role": "user",
                    "content": call.prompt,
                    "timestamp": call.created_at,
                }
            )
            chat_history.append(
                {
                    "id": str(call.id),
                    "role": "assistant",
                    "content": call.response,
                    "timestamp": call.created_at,
                }
            )

        return ChatHistoryResponse(
            project_id=str(project_id),
            chat_history=chat_history,
            total_messages=len(chat_history),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get chat history: {str(e)}"
        )


@router.get("/{project_id}/plan", response_model=ProjectPlanResponse)
async def get_project_plan(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get the current plan for a project"""
    try:
        # Get the project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get plan details directly from database
        plans = (
            db.query(Plan)
            .filter(Plan.project_id == project_id)
            .order_by(Plan.step_id)
            .all()
        )

        plan_summary = (
            {
                "exists": len(plans) > 0,
                "total_steps": len(plans),
                "steps": [
                    {
                        "step_id": plan.step_id,
                        "text": plan.text,
                        "created_at": plan.created_at,
                    }
                    for plan in plans
                ],
            }
            if plans
            else {"exists": False, "message": "No plan found for this project"}
        )

        # Get workflow details directly from database
        workflows = (
            db.query(Workflow)
            .filter(Workflow.project_id == project_id)
            .order_by(Workflow.created_at.desc())
            .all()
        )

        workflow_summary = (
            {
                "exists": len(workflows) > 0,
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
                    }
                    for wf in workflows
                ],
            }
            if workflows
            else {"exists": False, "message": "No workflows found for this project"}
        )

        return ProjectPlanResponse(
            project_id=str(project_id),
            plan=plan_summary,
            workflows=workflow_summary,
            project_status=project.status,
            mermaid_chart=project.mermaid_chart,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get project plan: {str(e)}"
        )


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(db: Session = Depends(get_db)):
    """List all projects for the current user"""
    try:
        # For now, we'll get all projects
        # In a real app, this would filter by authenticated user
        projects = db.query(Project).all()

        return [
            ProjectResponse(
                id=project.id,
                user_id=project.user_id,
                name=project.name,
                description=project.description,
                github_repo=project.github_repo,
                prompt=project.prompt,
                status=project.status,
                mermaid_chart=project.mermaid_chart,
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
            for project in projects
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve projects: {str(e)}"
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a project by ID"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return ProjectResponse(
            id=project.id,
            user_id=project.user_id,
            name=project.name,
            description=project.description,
            github_repo=project.github_repo,
            prompt=project.prompt,
            status=project.status,
            mermaid_chart=project.mermaid_chart,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve project: {str(e)}"
        )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID, request: ProjectUpdate, db: Session = Depends(get_db)
):
    """Update a project"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Update only provided fields
        if request.name is not None:
            project.name = request.name
        if request.description is not None:
            project.description = request.description
        if request.github_repo is not None:
            project.github_repo = request.github_repo
        if request.status is not None:
            project.status = request.status

        project.updated_at = datetime.now()

        db.commit()
        db.refresh(project)

        return ProjectResponse(
            id=project.id,
            user_id=project.user_id,
            name=project.name,
            description=project.description,
            github_repo=project.github_repo,
            prompt=project.prompt,
            status=project.status,
            mermaid_chart=project.mermaid_chart,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/{project_id}")
async def delete_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a project"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        db.delete(project)
        db.commit()

        return {"message": "Project deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to delete project: {str(e)}"
        )
