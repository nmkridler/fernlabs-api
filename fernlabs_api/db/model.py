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
    plans = relationship("Plan", back_populates="user")


class Project(Base):
    """Project model representing a user's workflow project"""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name = Column("name", String(255), nullable=False)
    description = Column("description", Text)
    github_repo = Column("github_repo", String(500))  # GitHub repository URL
    prompt = Column(
        "prompt", Text, nullable=False
    )  # User's prompt for workflow generation
    status = Column(
        "status", String(50), default="loading"
    )  # loading, completed, failed, active, archived, deleted
    mermaid_chart = Column("mermaid_chart", Text)  # Mermaid chart for the workflow
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
    plans = relationship("Plan", back_populates="project")
    agent_calls = relationship("AgentCall", back_populates="project")


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


class Plan(Base):
    """Plan model representing workflow planning steps"""

    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    step_id = Column("step_id", Integer, nullable=False)  # Ordering of plan steps
    text = Column("text", Text, nullable=False)  # Plan step content
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
    user = relationship("User", back_populates="plans")
    project = relationship("Project", back_populates="plans")


class AgentCall(Base):
    """Model for tracking agent calls and responses"""

    __tablename__ = "agent_calls"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    prompt = Column("prompt", Text, nullable=False)  # The prompt sent to the agent
    response = Column("response", Text, nullable=False)  # The agent's response
    created_at = Column(
        "created_at",
        DateTime,
        default=datetime.now(UTC),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    project = relationship("Project", back_populates="agent_calls")
