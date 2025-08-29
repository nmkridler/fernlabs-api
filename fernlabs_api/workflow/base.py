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
    connections: List[
        Dict[str, Any]
    ]  # List of connection objects with source, target, type, condition
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
    current_step_id: Optional[int] = None  # Track current execution step
    execution_path: List[int] = field(default_factory=list)  # Track execution path
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


def _parse_connections_from_plan(plan_text: str) -> List[Dict[str, Any]]:
    """Parse connections from the plan text, looking for indicators of loops, conditionals, etc."""
    connections = []
    lines = [line.strip() for line in plan_text.split("\n") if line.strip()]

    for i, line in enumerate(lines):
        line_lower = line.lower()

        # Look for loop indicators - more flexible pattern matching
        if any(
            keyword in line_lower
            for keyword in [
                "loop back",
                "loop to",
                "repeat",
                "iterate",
                "while",
                "for each",
            ]
        ):
            # Look for the target step (usually mentioned in the same line)
            # For example: "loop back to transformation" -> find step with "transformation"
            target_keywords = []
            if "loop back to" in line_lower:
                target_keywords = line_lower.split("loop back to")[1].strip().split()
            elif "loop to" in line_lower:
                target_keywords = line_lower.split("loop to")[1].strip().split()

            # Find the target step by looking for steps containing these keywords
            for j, target_line in enumerate(lines):
                if j != i and any(
                    keyword in target_line.lower() for keyword in target_keywords
                ):
                    connections.append(
                        {
                            "source": i + 1,
                            "target": j + 1,
                            "type": "loop_back",
                            "condition": "loop condition",
                            "label": "Loop back",
                        }
                    )
                    break

        # Look for conditional indicators - more flexible pattern matching
        if any(
            keyword in line_lower
            for keyword in ["if", "when", "check", "verify", "validate"]
        ):
            # Look for the next step that might be the "else" branch
            # For now, we'll create a conditional connection to the next step
            # and let the user specify the actual branching logic
            if i + 1 < len(lines):
                connections.append(
                    {
                        "source": i + 1,
                        "target": i + 2,
                        "type": "conditional",
                        "condition": "condition met",
                        "label": "Yes",
                    }
                )
                # Add a "No" branch to the step after next (if it exists)
                if i + 2 < len(lines):
                    connections.append(
                        {
                            "source": i + 1,
                            "target": i + 3,
                            "type": "conditional",
                            "condition": "condition not met",
                            "label": "No",
                        }
                    )

    # Add default sequential connections for steps without explicit connections
    for i in range(1, len(lines)):
        if not any(conn["source"] == i for conn in connections):
            connections.append(
                {
                    "source": i,
                    "target": i + 1,
                    "type": "next",
                    "condition": None,
                    "label": "Next",
                }
            )

    return connections


def _generate_plan_mermaid_chart_with_connections(
    plan_steps: List[str], connections: List[Dict[str, Any]]
) -> str:
    """
    Generate a Mermaid flowchart that shows the actual connections between steps,
    including loops, conditionals, and other non-linear flows.
    """
    if not plan_steps:
        return "flowchart TD\n    A[No Plan Available]"

    mermaid_lines = ["flowchart TD"]

    # Add nodes
    for i, step in enumerate(plan_steps, 1):
        node_id = f"S{i}"
        # Truncate long descriptions for readability
        label = step[:50] + "..." if len(step) > 50 else step
        # Escape quotes and special characters
        label = label.replace('"', '\\"').replace("'", "\\'")
        mermaid_lines.append(f'    {node_id}["{label}"]')

    # Add edges with different styles based on connection type
    for conn in connections:
        source = f"S{conn['source']}"
        target = f"S{conn['target']}"

        if conn["type"] == "loop_back":
            mermaid_lines.append(
                f"    {source} -.-> {target} : {conn.get('label', 'Loop')}"
            )
        elif conn["type"] == "conditional":
            condition = conn.get("label", "Condition")
            mermaid_lines.append(f"    {source} -->|{condition}| {target}")
        else:
            mermaid_lines.append(f"    {source} --> {target}")

    return "\n".join(mermaid_lines)


def _save_plan_connections_to_db(
    db: Session,
    project_id: uuid.UUID,
    connections: List[Dict[str, Any]],
    plan_steps: List[str],
):
    """Save plan connections to the database"""
    from fernlabs_api.db.model import PlanConnection, Plan

    # First, get the plan steps from the database to map step_id to UUID
    plan_entries = (
        db.query(Plan)
        .filter(Plan.project_id == project_id)
        .order_by(Plan.step_id)
        .all()
    )

    if len(plan_entries) != len(plan_steps):
        # Something went wrong with the plan creation
        return

    # Create a mapping from step_id to plan UUID
    step_to_uuid = {plan.step_id: plan.id for plan in plan_entries}

    # Save connections
    for conn in connections:
        source_uuid = step_to_uuid.get(conn["source"])
        target_uuid = step_to_uuid.get(conn["target"])

        if source_uuid and target_uuid:
            connection = PlanConnection(
                id=uuid.uuid4(),
                project_id=project_id,
                source_step_id=source_uuid,
                target_step_id=target_uuid,
                connection_type=conn["type"],
                condition=conn.get("condition"),
                label=conn.get("label"),
            )
            db.add(connection)

    db.commit()


def _get_next_execution_steps(
    db: Session, project_id: uuid.UUID, current_step_id: int
) -> List[Dict[str, Any]]:
    """Get the next possible execution steps based on current step and connections"""
    from fernlabs_api.db.model import PlanConnection, Plan

    # Get all outgoing connections from the current step
    current_plan = (
        db.query(Plan)
        .filter(Plan.project_id == project_id, Plan.step_id == current_step_id)
        .first()
    )

    if not current_plan:
        return []

    connections = (
        db.query(PlanConnection)
        .filter(
            PlanConnection.project_id == project_id,
            PlanConnection.source_step_id == current_plan.id,
        )
        .all()
    )

    next_steps = []
    for conn in connections:
        target_plan = db.query(Plan).filter(Plan.id == conn.target_step_id).first()
        if target_plan:
            next_steps.append(
                {
                    "step_id": target_plan.step_id,
                    "text": target_plan.text,
                    "connection_type": conn.connection_type,
                    "condition": conn.condition,
                    "label": conn.label,
                }
            )

    return next_steps


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
