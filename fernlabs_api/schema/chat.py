from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ChatMessage(BaseModel):
    """Schema for a chat message"""

    message: str


class ChatResponse(BaseModel):
    """Schema for chat response"""

    response: str
    project_status: str
    has_plan: bool


class ChatHistoryItem(BaseModel):
    """Schema for a chat history item"""

    id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime


class ChatHistoryResponse(BaseModel):
    """Schema for chat history response"""

    project_id: str
    chat_history: List[ChatHistoryItem]
    total_messages: int


class ProjectPlanResponse(BaseModel):
    """Schema for project plan response"""

    project_id: str
    plan: dict
    workflows: dict
    project_status: str
    mermaid_chart: Optional[str] = None
