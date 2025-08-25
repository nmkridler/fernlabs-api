from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class WorkflowGenerationRequest(BaseModel):
    """Schema for requesting workflow generation"""

    project_description: str
    project_type: Optional[str] = None
    requirements: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    preferred_ai_model: Optional[str] = None


class WorkflowNode(BaseModel):
    """Schema for a workflow node"""

    id: str
    name: str
    node_type: str  # task, decision, start, end
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class WorkflowEdge(BaseModel):
    """Schema for a workflow edge"""

    source: str
    target: str
    condition: Optional[str] = None  # For conditional transitions
    metadata: Optional[Dict[str, Any]] = None


class WorkflowGraph(BaseModel):
    """Schema for workflow graph structure"""

    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]


class StateVariable(BaseModel):
    """Schema for workflow state variables"""

    name: str
    type: str
    description: Optional[str] = None
    default_value: Optional[Any] = None
    required: bool = True


class DecisionPoint(BaseModel):
    """Schema for LLM decision points"""

    node_id: str
    prompt_template: str
    context_variables: List[str]
    output_schema: Dict[str, Any]


class WorkflowDefinition(BaseModel):
    """Complete workflow definition"""

    graph: WorkflowGraph
    state_schema: List[StateVariable]
    decision_points: List[DecisionPoint]
    entry_point: str
    exit_points: List[str]


class WorkflowBase(BaseModel):
    """Base workflow schema"""

    name: str
    description: Optional[str] = None


class WorkflowCreate(WorkflowBase):
    """Schema for creating a new workflow"""

    project_id: uuid.UUID
    workflow_definition: WorkflowDefinition
    generation_prompt: str


class WorkflowUpdate(BaseModel):
    """Schema for updating a workflow"""

    name: Optional[str] = None
    description: Optional[str] = None
    workflow_definition: Optional[WorkflowDefinition] = None
    status: Optional[str] = None


class WorkflowResponse(WorkflowBase):
    """Schema for workflow response"""

    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    workflow_graph: Dict[str, Any]  # JSON field from database
    state_schema: Dict[str, Any]  # JSON field from database
    decision_points: Optional[List[Any]] = None  # JSON field from database
    version: str
    status: str
    generation_prompt: str
    ai_model_used: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowExecutionRequest(BaseModel):
    """Schema for requesting workflow execution"""

    workflow_id: uuid.UUID
    initial_state: Optional[Dict[str, Any]] = None
    artifacts: Optional[List[uuid.UUID]] = None


class WorkflowExecutionResponse(BaseModel):
    """Schema for workflow execution response"""

    execution_id: str
    workflow_id: uuid.UUID
    status: str
    current_state: Optional[Dict[str, Any]] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None
    logs: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
