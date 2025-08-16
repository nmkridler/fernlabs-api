from datetime import datetime, UTC
import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    JSON,
    Integer,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column

# Import Base from the db module
from fernlabs_api.db import Base


class User(Base):
    """User model for authentication and project ownership"""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    email = Column("email", String(255), unique=True, nullable=False)
    name = Column("name", String(255))
    created_at = Column(
        "created_at",
        DateTime,
        default=datetime.now(UTC),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        "updated_at",
        DateTime,
        default=datetime.now(UTC),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    projects = relationship("Project", back_populates="user")
    workflows = relationship("Workflow", back_populates="user")


class Project(Base):
    """Project model representing a user's workflow project"""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name = Column("name", String(255), nullable=False)
    description = Column("description", Text)
    project_type = Column(
        "project_type", String(100)
    )  # e.g., "data_analysis", "ml_pipeline"
    github_repo = Column("github_repo", String(500))  # GitHub repository URL
    prompt = Column(
        "prompt", Text, nullable=False
    )  # User's prompt for workflow generation
    status = Column(
        "status", String(50), default="loading"
    )  # loading, completed, failed, active, archived, deleted
    created_at = Column(
        "created_at",
        DateTime,
        default=datetime.now(UTC),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        "updated_at",
        DateTime,
        default=datetime.now(UTC),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user = relationship("User", back_populates="projects")
    workflows = relationship("Workflow", back_populates="project")
    artifacts = relationship("Artifact", back_populates="project")


class Workflow(Base):
    """Workflow model representing an AI-generated workflow"""

    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name = Column("name", String(255), nullable=False)
    description = Column("description", Text)

    # Workflow definition using pydantic-graph
    workflow_graph = Column("workflow_graph", JSON, nullable=False)  # Graph structure
    state_schema = Column(
        "state_schema", JSON, nullable=False
    )  # State variables schema
    decision_points = Column("decision_points", JSON)  # LLM decision points

    # Workflow metadata
    version = Column("version", String(50), default="1.0.0")
    status = Column("status", String(50), default="draft")  # draft, active, archived

    # AI generation metadata
    generation_prompt = Column("generation_prompt", Text)  # Original user request
    ai_model_used = Column("ai_model_used", String(100))

    created_at = Column(
        "created_at",
        DateTime,
        default=datetime.now(UTC),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        "updated_at",
        DateTime,
        default=datetime.now(UTC),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    project = relationship("Project", back_populates="workflows")
    user = relationship("User", back_populates="workflows")
    executions = relationship("WorkflowExecution", back_populates="workflow")


class WorkflowExecution(Base):
    """Model for tracking workflow executions"""

    __tablename__ = "workflow_executions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"))
    execution_id = Column("execution_id", String(255), unique=True, nullable=False)

    # Execution state
    status = Column(
        "status", String(50), default="running"
    )  # running, completed, failed, paused
    current_state = Column("current_state", JSON)  # Current workflow state
    state_history = Column("state_history", JSON)  # State transition history

    # Execution metadata
    started_at = Column("started_at", DateTime, default=datetime.now(UTC))
    completed_at = Column("completed_at", DateTime)
    total_duration = Column("total_duration", Integer)  # Duration in seconds

    # Results and logs
    results = Column("results", JSON)  # Final execution results
    logs = Column("logs", Text)  # Execution logs
    error_message = Column("error_message", Text)  # Error details if failed

    # Relationships
    workflow = relationship("Workflow", back_populates="executions")


class Artifact(Base):
    """Model for storing workflow artifacts (data, files, etc.)"""

    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    name = Column("name", String(255), nullable=False)
    description = Column("description", Text)

    # Artifact metadata
    artifact_type = Column("artifact_type", String(100))  # csv, json, model, etc.
    file_path = Column("file_path", String(500))  # Path to stored artifact
    file_size = Column("file_size", Integer)  # Size in bytes
    mime_type = Column("mime_type", String(100))

    # Metadata
    tags = Column("tags", JSON)  # JSON array of tags
    artifact_metadata = Column("artifact_metadata", JSON)  # Additional metadata

    created_at = Column(
        "created_at",
        DateTime,
        default=datetime.now(UTC),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        "updated_at",
        DateTime,
        default=datetime.now(UTC),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    project = relationship("Project", back_populates="artifacts")
