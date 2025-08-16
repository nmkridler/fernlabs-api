"""
Projects API routes
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime

from fernlabs_api.schema.project import ProjectCreate, ProjectUpdate, ProjectResponse
from fernlabs_api.db import get_db
from fernlabs_api.db.model import Project, User
from fernlabs_api.workflow.tasks import generate_workflow_background

router = APIRouter()


@router.post("/", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create a new project and launch background workflow generation"""

    # For now, we'll use a placeholder user_id
    # In a real app, this would come from authentication
    user_id = uuid.uuid4()  # TODO: Get from auth context

    try:
        # Create new project with loading status
        project = Project(
            id=uuid.uuid4(),
            user_id=user_id,
            name=request.name,
            description=request.description,
            project_type=request.project_type,
            github_repo=request.github_repo,
            prompt=request.prompt,
            status="loading",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        db.add(project)
        db.commit()
        db.refresh(project)

        # Add background task for workflow generation
        # This will run asynchronously and update the project status
        background_tasks.add_task(
            generate_workflow_background, str(project.id), str(user_id)
        )

        # Return the project immediately with loading status
        return ProjectResponse(
            id=project.id,
            user_id=project.user_id,
            name=project.name,
            description=project.description,
            project_type=project.project_type,
            github_repo=project.github_repo,
            prompt=project.prompt,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create project: {str(e)}"
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
                project_type=project.project_type,
                github_repo=project.github_repo,
                prompt=project.prompt,
                status=project.status,
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
            project_type=project.project_type,
            github_repo=project.github_repo,
            prompt=project.prompt,
            status=project.status,
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
        if request.project_type is not None:
            project.project_type = request.project_type
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
            project_type=project.project_type,
            github_repo=project.github_repo,
            prompt=project.prompt,
            status=project.status,
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
