"""
Background tasks for workflow generation using FastAPI BackgroundTasks
"""

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any
import uuid
from datetime import datetime
import asyncio

from fernlabs_api.settings import APISettings
from fernlabs_api.workflow.generator import WorkflowGenerator
from fernlabs_api.schema.workflow import WorkflowGenerationRequest
from fernlabs_api.db.model import Project, Workflow, Base
from fernlabs_api.schema.workflow import WorkflowCreate

settings = APISettings()

# Create database engine for background tasks
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def generate_workflow_background(project_id: str, user_id: str):
    """
    Background task to generate workflow from user prompt

    Args:
        project_id: UUID of the project
        user_id: UUID of the user
    """
    # Run the synchronous database operations in a thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _generate_workflow_sync, project_id, user_id
    )


def _generate_workflow_sync(project_id: str, user_id: str):
    """
    Synchronous version of workflow generation for running in thread pool
    """
    db = SessionLocal()

    try:
        # Get the project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Create workflow generation request
        workflow_request = WorkflowGenerationRequest(
            project_description=project.prompt,
            project_type=project.project_type or "general",
        )

        # Initialize workflow generator
        generator = WorkflowGenerator(settings)

        # Generate workflow definition
        workflow_definition = generator.generate_workflow(workflow_request)

        # Create workflow in database
        workflow = Workflow(
            id=uuid.uuid4(),
            project_id=project.id,
            user_id=uuid.UUID(user_id),
            name=f"Workflow for {project.name}",
            description=f"AI-generated workflow based on: {project.prompt}",
            workflow_graph=workflow_definition.graph.model_dump(),
            state_schema=workflow_definition.state_schema,
            decision_points=workflow_definition.decision_points,
            version="1.0.0",
            status="draft",
            generation_prompt=project.prompt,
            ai_model_used="gpt-4o" if settings.openai_api_key else "gemini-1.5-flash",
        )

        db.add(workflow)

        # Update project status to completed
        project.status = "completed"
        project.updated_at = datetime.now()

        db.commit()

        return {
            "status": "success",
            "project_id": str(project_id),
            "workflow_id": str(workflow.id),
        }

    except Exception as e:
        # Update project status to failed
        if project:
            project.status = "failed"
            project.updated_at = datetime.now()
            db.commit()

        db.rollback()
        raise e

    finally:
        db.close()


async def generate_workflow_code_background(workflow_id: str):
    """
    Background task to generate Python code for a workflow

    Args:
        workflow_id: UUID of the workflow
    """
    # Run the synchronous database operations in a thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _generate_workflow_code_sync, workflow_id)


def _generate_workflow_code_sync(workflow_id: str):
    """
    Synchronous version of code generation for running in thread pool
    """
    db = SessionLocal()

    try:
        # Get the workflow
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        # Initialize workflow generator
        generator = WorkflowGenerator(settings)

        # Generate Python code
        code = generator.generate_python_code(workflow.workflow_definition)

        # Generate unit tests
        tests = generator.generate_unit_tests(workflow.workflow_definition, code)

        # Store code and tests (you might want to create a new table for this)
        # For now, we'll just return them

        return {
            "status": "success",
            "workflow_id": str(workflow_id),
            "code": code,
            "tests": tests,
        }

    except Exception as e:
        db.rollback()
        raise e

    finally:
        db.close()
