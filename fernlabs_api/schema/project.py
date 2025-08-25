from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class ProjectBase(BaseModel):
    """Base project schema"""

    name: str
    description: Optional[str] = None
    github_repo: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Schema for creating a new project"""

    user_id: uuid.UUID  # User ID for the project owner
    prompt: str  # User's prompt for workflow generation


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""

    name: Optional[str] = None
    description: Optional[str] = None
    github_repo: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(ProjectBase):
    """Schema for project response"""

    id: uuid.UUID
    user_id: uuid.UUID
    prompt: str
    status: str  # "loading", "completed", "failed"
    mermaid_chart: Optional[str] = (
        None  # Mermaid chart syntax for workflow visualization
    )
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
