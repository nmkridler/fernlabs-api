#!/usr/bin/env python3
"""
Example usage of the refactored WorkflowAgent using pydantic-graph
"""

import asyncio
import uuid
from fernlabs_api.workflow.generator import WorkflowAgent
from fernlabs_api.settings import APISettings


async def main():
    """Example of running the workflow"""

    # Initialize settings (you'll need to set your API keys)
    settings = APISettings(
        api_model_name="gpt-4o-mini",  # or your preferred model
        api_model_provider="openai",  # or "mistral", "google"
        api_model_key="your-api-key-here",
    )

    # Create the workflow agent
    agent = WorkflowAgent(settings)

    # Example project data
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    # Example chat history
    chat_history = [
        {
            "role": "user",
            "content": "I want to build a web application for task management",
        },
        {
            "role": "assistant",
            "content": "That sounds like a great project! What kind of features are you looking for?",
        },
        {
            "role": "user",
            "content": "I need user authentication, task creation, and basic CRUD operations",
        },
    ]

    print("=== Workflow Agent Demo ===")
    print(f"User ID: {user_id}")
    print(f"Project ID: {project_id}")
    print(f"Chat history length: {len(chat_history)}")

    # Generate Mermaid diagram
    print("\n=== Workflow Diagram ===")
    mermaid_diagram = agent.generate_mermaid_diagram()
    print(mermaid_diagram)

    print("\n=== Workflow Execution ===")
    print("Note: This would require a database connection and valid API keys")
    print("The workflow would execute as follows:")
    print("1. CreatePlan -> Creates initial project plan")
    print("2. AssessPlan -> Evaluates if plan needs improvement")
    print("3. WaitForUserInput -> Waits for user response (if needed)")
    print("4. EditPlan -> Improves plan based on user feedback")
    print("5. Back to AssessPlan -> Checks if further improvements needed")
    print("6. End -> When plan is complete")

    # Example of how you would run the workflow (commented out due to missing deps)
    """
    try:
        result = await agent.run_workflow(
            user_id=user_id,
            project_id=project_id,
            chat_history=chat_history,
            db=db_session,  # You'd need a database session
            user_response=None  # Initial run, no user response yet
        )

        print(f"Workflow completed with output: {result['output']}")
        print(f"Final state: {result['final_state']}")
        print(f"Execution history: {result['history']}")

    except Exception as e:
        print(f"Error running workflow: {e}")
    """

    print("\n=== State Management ===")
    print("The workflow maintains state throughout execution:")
    print("- Current plan content")
    print("- Whether plan needs improvement")
    print("- Follow-up questions asked")
    print("- User responses received")
    print("- Final plan output")

    print("\n=== Benefits of pydantic-graph ===")
    print("1. Clear workflow visualization with Mermaid diagrams")
    print("2. Type-safe state management")
    print("3. Automatic dependency injection")
    print("4. Easy to extend and modify workflow logic")
    print("5. Built-in state persistence capabilities")
    print("6. Better error handling and debugging")


if __name__ == "__main__":
    asyncio.run(main())
