"""
Base utilities and types for workflow nodes.
"""

from typing import List, Dict, Any, Optional
import uuid
import re
from html import escape
from dataclasses import field
from sqlalchemy.orm import Session
from pydantic import BaseModel

from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.google import GoogleModel

from fernlabs_api.settings import APISettings
from fernlabs_api.db.model import Plan, Project, AgentCall

# Regular expression for parsing plan steps
STEP_RE = re.compile(r"^\s*(\d+)\.\s*([^:]+?)(?:\s*:\s*(.*))?\s*$")


class PlanDependencies(BaseModel):
    """Dependencies for plan creation including user context and database access"""

    user_id: uuid.UUID
    project_id: uuid.UUID
    chat_history: List[
        Dict[str, str]
    ]  # List of {"role": "user/assistant", "content": "message"}
    db: Any  # Accept any type for testing flexibility

    model_config = {"arbitrary_types_allowed": True}


class PlanResponse(BaseModel):
    """Response containing the created or edited plan"""

    plan: str
    mermaid_chart: str


class WorkflowState(BaseModel):
    """State maintained throughout the workflow execution"""

    user_id: uuid.UUID
    project_id: uuid.UUID
    chat_history: List[Dict[str, str]] = field(default_factory=list)
    current_plan: Optional[str] = None
    mermaid_chart: Optional[str] = None
    plan_needs_improvement: bool = False
    followup_question: Optional[str] = None
    user_response: Optional[str] = None
    final_plan: Optional[PlanResponse] = None
    db: Any = None

    model_config = {"arbitrary_types_allowed": True}


class WorkflowDependencies(BaseModel):
    """Dependencies injected into the workflow"""

    settings: APISettings
    db: Session

    model_config = {"arbitrary_types_allowed": True}


def _parse_plan_into_steps(plan_text: str) -> List[str]:
    """Parse the generated plan text into individual steps"""
    # Simple parsing - split by numbered lists or bullet points
    lines = plan_text.split("\n")
    steps = []
    current_step = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if this is a new step (starts with number, bullet, or is a phase header)
        if (
            line[0].isdigit()
            and line[1] in [".", ")", " "]
            or line.startswith(("-", "•", "*"))
            or line.isupper()  # Phase headers are often in caps
            or line.endswith(":")
            or line.startswith("Phase")
            or line.startswith("Step")
        ):
            if current_step:
                steps.append(current_step.strip())
            current_step = line
        else:
            current_step += " " + line

    # Add the last step
    if current_step:
        steps.append(current_step.strip())

    # If no clear steps found, split by paragraphs
    if len(steps) <= 1:
        steps = [step.strip() for step in plan_text.split("\n\n") if step.strip()]

    return steps


def _generate_plan_mermaid_chart(plan_steps: List[str]) -> str:
    """
    Parse lines like '1. Load Data: load the csv data' into a Mermaid flowchart TD.
    - Lines may omit the description ('2. Transform Data')
    - Ignores blank/comment lines
    - Orders nodes by the numeric prefix
    - Escapes characters that could break Mermaid/HTML

    Args:
        text: the numbered steps block
        title_desc_sep: separator between title and description in node label (default: HTML <br/>)

    Returns:
        str: Mermaid code block (string) for a flowchart TD
    """
    steps = []
    for line in plan_steps:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = STEP_RE.match(line)
        if not m:
            # skip non-matching lines gracefully
            continue
        n, title, desc = m.group(1), m.group(2).strip(), (m.group(3) or "").strip()
        # Escape for safety; Mermaid supports simple HTML in labels
        title = escape(title)
        desc = escape(desc)
        steps.append((int(n), title, desc))

    if not steps:
        raise ValueError(
            "No steps parsed. Make sure lines look like '1. Title: description'."
        )

    # Sort by the numeric index just in case lines are out of order
    steps.sort(key=lambda x: x[0])

    # Build nodes
    node_lines = []
    edge_lines = []

    for idx, (n, title, desc) in enumerate(steps, start=1):
        node_id = f"S{idx}"
        label = title if not desc else f"{title}<br/>{desc[:20]}..."
        node_lines.append(f'    {node_id}["{label}"]:::big')

        if idx > 1:
            edge_lines.append(f"    S{idx - 1} --> {node_id}")

    # Assemble Mermaid
    mermaid = ["flowchart TD"]
    mermaid.extend(node_lines)
    mermaid.extend(edge_lines)
    mermaid.extend(["classDef big font-size:18px;"])

    return "\n".join(mermaid)


def _save_mermaid_chart_to_project(
    db: Session, project_id: uuid.UUID, mermaid_chart: str
):
    """Save the mermaid chart to the project in the database"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        project.mermaid_chart = mermaid_chart
        db.commit()


def _update_project_status(db: Session, project_id: uuid.UUID, status: str):
    """Update the project status in the database"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        project.status = status
        db.commit()


async def _log_agent_call(
    db: Session, project_id: uuid.UUID, prompt: str, response: str
):
    """Log an agent call and response to the database"""
    agent_call = AgentCall(
        id=uuid.uuid4(),
        project_id=project_id,
        prompt=prompt,
        response=response,
    )
    db.add(agent_call)
    db.commit()


def _model_factory(model_name: str, provider_name: str, api_key: str):
    """Create a provider based on the model name"""

    if provider_name == "mistral":
        return MistralModel(model_name, provider=MistralProvider(api_key=api_key))
    elif provider_name == "openai":
        return OpenAIModel(model_name, provider=OpenAIProvider(api_key=api_key))
    elif provider_name == "google":
        return GoogleModel(model_name, provider=GoogleProvider(api_key=api_key))

    raise ValueError(f"Unsupported provider: {provider_name}")
