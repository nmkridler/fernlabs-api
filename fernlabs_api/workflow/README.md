# Workflow System Architecture

This directory contains the AI-powered workflow system that has been refactored into a modular, maintainable structure.

## Directory Structure

```
workflow/
├── __init__.py              # Main package exports
├── base.py                  # Shared utilities, types, and base classes
├── workflow_agent.py        # Main WorkflowAgent class that orchestrates everything
├── generator.py             # Backward compatibility layer
├── nodes/                   # Individual workflow node implementations
│   ├── __init__.py         # Node package exports
│   ├── create_plan.py      # CreatePlan node
│   ├── assess_plan.py      # AssessPlan node
│   ├── wait_for_user_input.py # WaitForUserInput node
│   └── edit_plan.py        # EditPlan node
└── README.md               # This file
```

## Architecture Overview

The workflow system has been refactored from a single monolithic file into a modular structure:

### 1. Base Module (`base.py`)
- **Shared Types**: `WorkflowState`, `WorkflowDependencies`, `PlanResponse`, `PlanDependencies`
- **Utility Functions**: Plan parsing, Mermaid chart generation, database operations
- **Common Dependencies**: Model factory, logging, status updates

### 2. Node Modules (`nodes/`)
Each workflow node is implemented as a separate class in its own file:

- **`CreatePlan`**: Generates initial project plans from conversation history
- **`AssessPlan`**: Evaluates plan quality and determines if follow-up is needed
- **`WaitForUserInput`**: Pauses workflow until user provides response
- **`EditPlan`**: Improves existing plans based on user feedback

### 3. Main Agent (`workflow_agent.py`)
- **`WorkflowAgent`**: Main class that orchestrates the entire workflow
- **Workflow Graph**: Defines the flow between nodes using pydantic-graph
- **Utility Methods**: Plan management, agent call tracking, workflow statistics

### 4. Backward Compatibility (`generator.py`)
- Maintains the original import structure for existing code
- Re-exports all classes and functions from the new structure
- Ensures no breaking changes for existing implementations

## Key Benefits of Refactoring

1. **Modularity**: Each node is self-contained and easier to understand
2. **Maintainability**: Changes to one node don't affect others
3. **Testability**: Individual nodes can be tested in isolation
4. **Extensibility**: New nodes can be easily added
5. **Readability**: Smaller, focused files are easier to navigate
6. **Reusability**: Common utilities are shared across nodes

## Usage

### Basic Usage (New Structure)
```python
from fernlabs_api.workflow import WorkflowAgent
from fernlabs_api.settings import APISettings

settings = APISettings()
agent = WorkflowAgent(settings)

# Run workflow
result = await agent.run_workflow(
    user_id=user_id,
    project_id=project_id,
    chat_history=chat_history,
    db=db_session
)
```

### Direct Node Usage
```python
from fernlabs_api.workflow.nodes import CreatePlan, AssessPlan
from fernlabs_api.workflow.base import WorkflowState, WorkflowDependencies

# Use individual nodes if needed
create_plan = CreatePlan()
# ... configure and run
```

### Backward Compatibility
```python
# Existing code continues to work unchanged
from fernlabs_api.workflow.generator import WorkflowAgent
```

## Adding New Nodes

To add a new workflow node:

1. Create a new file in `nodes/` (e.g., `new_node.py`)
2. Inherit from `BaseNode[WorkflowState, WorkflowDependencies]`
3. Implement the `run()` method
4. Add the node to `nodes/__init__.py`
5. Update the workflow graph in `workflow_agent.py`

Example:
```python
@dataclass
class NewNode(BaseNode[WorkflowState, WorkflowDependencies]):
    async def run(self, ctx: GraphRunContext[WorkflowState, WorkflowDependencies]):
        # Node logic here
        return NextNode()
```

## Dependencies

- **pydantic-graph**: Workflow orchestration and state management
- **pydantic-ai**: AI agent integration
- **SQLAlchemy**: Database operations
- **loguru**: Logging

## Testing

Each node can be tested independently:
```python
# Test individual node
async def test_create_plan():
    node = CreatePlan()
    # Test node logic
```

The modular structure makes it easier to mock dependencies and test edge cases.
