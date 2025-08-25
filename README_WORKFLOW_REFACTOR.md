# Workflow Refactor: Using pydantic-graph

This document explains the refactored workflow system that now uses `pydantic-graph` instead of the previous agent-based approach.

## Overview

The workflow has been refactored to use `pydantic-graph`, which provides:
- **Clear workflow visualization** with Mermaid diagrams
- **Type-safe state management** throughout execution
- **Automatic dependency injection** for database and settings
- **Better error handling** and debugging capabilities
- **State persistence** for long-running workflows

## Workflow Flow

The new workflow follows this pattern:

```
CreatePlan → AssessPlan → [WaitForUserInput → EditPlan → AssessPlan] → End
```

### 1. CreatePlan Node
- **Purpose**: Creates the initial project plan from conversation history
- **Input**: Chat history, user context
- **Output**: Comprehensive project plan
- **Next**: Always goes to AssessPlan

### 2. AssessPlan Node
- **Purpose**: Evaluates if the plan needs improvement
- **Input**: Current plan, chat history
- **Output**: Either "PLAN_COMPLETE" or a follow-up question
- **Next**:
  - If complete → End (with final plan)
  - If needs improvement → WaitForUserInput

### 3. WaitForUserInput Node
- **Purpose**: Represents waiting for user response to follow-up question
- **Input**: Follow-up question from AssessPlan
- **Output**: User response (injected into state)
- **Next**:
  - If user response available → EditPlan
  - If no response yet → End (pauses workflow and returns question to client)
- **Status Updates**: Updates project status to "needs_input" and pauses workflow
- **Client Response**: Returns follow-up question to client for user input

### 4. EditPlan Node
- **Purpose**: Improves the plan based on user feedback
- **Input**: Original plan, user response, follow-up question
- **Output**: Improved plan
- **Next**: Always goes back to AssessPlan

### 5. End
- **Purpose**: Workflow completion
- **Output**: Final PlanResponse object

## State Management

The workflow maintains state throughout execution using `WorkflowState`:

```python
class WorkflowState(BaseModel):
    user_id: uuid.UUID
    project_id: uuid.UUID
    chat_history: List[Dict[str, str]]
    current_plan: Optional[str] = None
    plan_needs_improvement: bool = False
    followup_question: Optional[str] = None
    user_response: Optional[str] = None
    final_plan: Optional[PlanResponse] = None
    db: Any = None
```

## Dependencies

Dependencies are injected using `WorkflowDependencies`:

```python
class WorkflowDependencies(BaseModel):
    settings: APISettings
    db: Session
```

## Usage

### Basic Usage

```python
from fernlabs_api.workflow.generator import WorkflowAgent
from fernlabs_api.settings import APISettings

# Initialize the agent
settings = APISettings(
    api_model_name="gpt-4o-mini",
    api_model_provider="openai",
    api_model_key="your-api-key"
)
agent = WorkflowAgent(settings)

# Run the workflow
result = await agent.run_workflow(
    user_id=user_id,
    project_id=project_id,
    chat_history=chat_history,
    db=db_session,
    user_response=None  # For initial run
)
```

### Generating Mermaid Diagrams

```python
# Generate a visual representation of the workflow
mermaid_diagram = agent.generate_mermaid_diagram()
print(mermaid_diagram)
```

### Handling User Input

For interactive workflows where you need to get user input:

```python
# First run - creates plan and assesses it
result1 = await agent.run_workflow(
    user_id=user_id,
    project_id=project_id,
    chat_history=chat_history,
    db=db_session
)

# Check if follow-up is needed
if result1['final_state'].plan_needs_improvement:
    followup_question = result1['final_state'].followup_question
    print(f"Follow-up question: {followup_question}")

    # Get user response
    user_response = input("Your response: ")

    # Continue workflow with user response
    result2 = await agent.run_workflow(
        user_id=user_id,
        project_id=project_id,
        chat_history=chat_history,
        db=db_session,
        user_response=user_response
    )
```

### Workflow Resumption

The new workflow system supports pausing and resuming workflows:

```python
# Resume a workflow that was waiting for user input
result = await agent.resume_workflow(
    user_id=user_id,
    project_id=project_id,
    chat_history=chat_history,
    db=db_session,
    user_response="User's response to follow-up question"
)
```

**Key Benefits:**
- **Pause and Resume**: Workflows can pause while waiting for user input
- **State Persistence**: All workflow state is maintained during pauses
- **Flexible Execution**: Can resume from exactly where it left off
- **Better User Experience**: Users can provide input at their own pace

### Workflow Pausing

When a workflow needs user input, it automatically pauses and returns the follow-up question:

```python
# Run workflow (may pause for user input)
result = await agent.run_workflow(
    user_id=user_id,
    project_id=project_id,
    chat_history=chat_history,
    db=db_session
)

# Check if workflow is waiting for input
if result.get("waiting_for_input", False):
    followup_question = result.get("followup_question")
    print(f"Workflow paused. Please answer: {followup_question}")

    # Get user response and resume
    user_response = input("Your answer: ")
    result = await agent.resume_workflow(
        user_id=user_id,
        project_id=project_id,
        chat_history=chat_history,
        db=db_session,
        user_response=user_response
    )
```

**Pause Behavior:**
- **Automatic Pausing**: Workflow pauses when `WaitForUserInput` is reached without a response
- **Question Return**: Client receives the follow-up question and can display it to the user
- **Status Update**: Project status is set to "needs_input" during the pause
- **Resume Point**: Workflow can resume exactly from where it paused

## Benefits of the Refactor

### 1. **Clear Visualization**
- Mermaid diagrams show exactly how the workflow flows
- Easy to understand and modify the workflow logic
- Better documentation of the process

### 2. **Type Safety**
- All state transitions are type-checked
- Compile-time validation of workflow structure
- Better IDE support and error catching

### 3. **State Management**
- Centralized state that persists throughout execution
- Easy to inspect and debug workflow state
- Support for long-running workflows

### 4. **Dependency Injection**
- Clean separation of concerns
- Easy to test individual nodes
- Flexible configuration management

### 5. **Extensibility**
- Easy to add new nodes
- Simple to modify workflow logic
- Clear patterns for common operations

## Migration from Old System

The old `WorkflowAgent` class has been refactored but maintains backward compatibility for utility methods:

- `get_project_plan()` - Still works as before
- `get_plan_summary()` - Still works as before
- `get_project_agent_calls()` - Still works as before
- All other utility methods remain unchanged

The main change is in how workflows are executed - now using the graph-based approach instead of the tool-based agent system.

## Example Workflow Execution

```python
# This would create a workflow that:
# 1. Creates a plan for a task management app
# 2. Assesses if the plan needs more details
# 3. Asks follow-up questions if needed
# 4. Improves the plan based on user responses
# 5. Continues until the plan is complete

chat_history = [
    {"role": "user", "content": "I want to build a task management app"},
    {"role": "assistant", "content": "What features do you need?"},
    {"role": "user", "content": "User auth, CRUD operations, and notifications"}
]

result = await agent.run_workflow(
    user_id=user_id,
    project_id=project_id,
    chat_history=chat_history,
    db=db_session
)
```

## Future Enhancements

The new architecture makes it easy to add:

- **Parallel execution** of independent nodes
- **Conditional branching** based on complex logic
- **Error handling nodes** for failed operations
- **Human-in-the-loop** nodes for manual review
- **Integration nodes** with external systems
- **Monitoring and observability** throughout execution

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `pydantic-graph` is installed
2. **Type Errors**: Check that your state and dependency types match
3. **Database Errors**: Verify database session is properly configured
4. **API Errors**: Check your API keys and model configuration

### Debugging

- Use `agent.generate_mermaid_diagram()` to visualize the workflow
- Check the `result['history']` to see execution path
- Inspect `result['final_state']` for current workflow state
- Use logging to track node execution

## Conclusion

The refactor to `pydantic-graph` provides a more robust, maintainable, and extensible workflow system. The clear separation of concerns, type safety, and visual representation make it easier to understand, debug, and enhance the workflow logic.
