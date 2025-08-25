"""
Example usage of the WorkflowAgent with create_plan functionality
"""

import asyncio
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fernlabs_api.workflow.generator import WorkflowAgent, PlanDependencies
from fernlabs_api.settings import APISettings
from fernlabs_api.db.model import Plan


async def example_create_plan():
    """Example of creating a plan using the WorkflowAgent"""

    # Initialize settings
    settings = APISettings()

    # Create database session
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Create the workflow agent
        agent = WorkflowAgent(settings)

        # Example user and project IDs
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()

        # Example chat history
        chat_history = [
            {
                "role": "user",
                "content": "I want to build a data pipeline for customer analytics",
            },
            {
                "role": "assistant",
                "content": "That sounds like a great project! What kind of data sources do you have?",
            },
            {
                "role": "user",
                "content": "We have customer transaction data in CSV files and user behavior data from our web app",
            },
            {
                "role": "assistant",
                "content": "Perfect! Let me help you create a comprehensive plan for this data pipeline.",
            },
        ]

        # Create dependencies
        deps = PlanDependencies(
            user_id=user_id, project_id=project_id, chat_history=chat_history, db=db
        )

        # Create a plan using the agent
        result = await agent.agent.run(
            "Create a comprehensive plan for building a data pipeline for customer analytics",
            deps=deps,
        )

        print("Plan created successfully!")
        print(f"Summary: {result.output.summary}")
        print(f"Key Phases: {result.output.key_phases}")
        print(f"Estimated Duration: {result.output.estimated_duration}")

        # Verify the plan was saved to the database
        saved_plans = (
            db.query(Plan)
            .filter(Plan.user_id == user_id, Plan.project_id == project_id)
            .order_by(Plan.step_id)
            .all()
        )

        print(f"\nSaved {len(saved_plans)} plan steps to database:")
        for plan in saved_plans:
            print(f"Step {plan.step_id}: {plan.text[:100]}...")

        return user_id, project_id

    finally:
        db.close()


async def example_edit_plan(user_id: uuid.UUID, project_id: uuid.UUID):
    """Example of editing an existing plan using the WorkflowAgent"""

    # Initialize settings
    settings = APISettings(
        api_model_provider="mistral",
        api_model_name="mistral:mistral-large-latest",
        api_model_key="your_mistral_api_key_here",
    )

    # Create database session
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Create the workflow agent
        agent = WorkflowAgent(settings)

        # Get the existing plan summary
        plan_summary = agent.get_plan_summary(db, user_id, project_id)
        print(f"Current plan has {plan_summary['total_steps']} steps")

        # Example updated chat history with new requirements
        updated_chat_history = [
            {
                "role": "user",
                "content": "I want to build a data pipeline for customer analytics",
            },
            {
                "role": "assistant",
                "content": "That sounds like a great project! What kind of data sources do you have?",
            },
            {
                "role": "user",
                "content": "We have customer transaction data in CSV files and user behavior data from our web app",
            },
            {
                "role": "assistant",
                "content": "Perfect! Let me help you create a comprehensive plan for this data pipeline.",
            },
            {
                "role": "user",
                "content": "Actually, I also need to add real-time streaming capabilities and machine learning predictions",
            },
            {
                "role": "assistant",
                "content": "Great addition! Let me update the plan to include real-time streaming and ML components.",
            },
        ]

        # Create dependencies for editing
        deps = PlanDependencies(
            user_id=user_id,
            project_id=project_id,
            chat_history=updated_chat_history,
            db=db,
        )

        # Edit the existing plan using the agent
        result = await agent.agent.run(
            "Update the existing plan to include real-time streaming and machine learning capabilities",
            deps=deps,
        )

        print("\nPlan updated successfully!")
        print(f"Updated Summary: {result.output.summary}")
        print(f"Updated Key Phases: {result.output.key_phases}")
        print(f"Updated Estimated Duration: {result.output.estimated_duration}")

        # Verify the updated plan was saved to the database
        updated_plans = (
            db.query(Plan)
            .filter(Plan.user_id == user_id, Plan.project_id == project_id)
            .order_by(Plan.step_id)
            .all()
        )

        print(f"\nUpdated plan now has {len(updated_plans)} steps:")
        for plan in updated_plans:
            print(f"Step {plan.step_id}: {plan.text[:100]}...")

    finally:
        db.close()


async def example_translate_plan_to_workflow(user_id: uuid.UUID, project_id: uuid.UUID):
    """Example of translating a plan into workflow structure using the WorkflowAgent"""

    # Initialize settings
    settings = APISettings(
        api_model_provider="mistral",
        api_model_name="mistral:mistral-large-latest",
        api_model_key="your_mistral_api_key_here",
    )

    # Create database session
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Create the workflow agent
        agent = WorkflowAgent(settings)

        # Get the existing plan
        plan_summary = agent.get_plan_summary(db, user_id, project_id)
        if not plan_summary["exists"]:
            print("No plan found to translate")
            return

        # Get the plan text
        existing_plans = agent.get_project_plan(db, user_id, project_id)
        plan_text = "\n\n".join([plan.text for plan in existing_plans])

        print(
            f"Translating plan with {plan_summary['total_steps']} steps to workflow structure..."
        )

        # Create dependencies for workflow generation
        deps = PlanDependencies(
            user_id=user_id,
            project_id=project_id,
            chat_history=[
                {
                    "role": "user",
                    "content": "Please convert this plan into a structured workflow with nodes and relationships",
                }
            ],
            db=db,
        )

        # Translate plan to workflow structure
        result = await agent.agent.run(
            f"Convert this plan into a workflow structure for a data pipeline project:\n\n{plan_text}",
            deps=deps,
        )

        print("Workflow structure generated successfully!")
        print(f"Generated {len(result.output.nodes)} nodes")
        print(f"Generated {len(result.output.edges)} edges")
        print(f"Generated {len(result.output.state_variables)} state variables")
        print(f"Generated {len(result.output.decision_points)} decision points")

        # Get workflow summary from database
        workflow_summary = agent.get_workflow_summary(db, user_id, project_id)
        if workflow_summary["exists"]:
            print(f"\nWorkflow saved to database:")
            for wf in workflow_summary["workflows"]:
                print(
                    f"- {wf['name']}: {wf['node_count']} nodes, {wf['edge_count']} edges"
                )
                print(f"  Status: {wf['status']}, Version: {wf['version']}")

    finally:
        db.close()


async def example_create_complete_workflow():
    """Example of creating a complete workflow with plan, nodes, and mermaid chart"""

    # Initialize settings
    settings = APISettings(
        api_model_provider="mistral",
        api_model_name="mistral:mistral-large-latest",
        api_model_key="your_mistral_api_key_here",
    )

    # Create database session
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Create the workflow agent
        agent = WorkflowAgent(settings)

        # Example user and project IDs
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()

        # Example chat history
        chat_history = [
            {
                "role": "user",
                "content": "I need a complete workflow for building a machine learning model",
            },
            {
                "role": "assistant",
                "content": "I'll help you create a comprehensive ML workflow plan and structure.",
            },
        ]

        # Create dependencies
        deps = PlanDependencies(
            user_id=user_id, project_id=project_id, chat_history=chat_history, db=db
        )

        # Create complete workflow
        result = await agent.create_complete_workflow(
            project_description="Build a machine learning model for customer churn prediction",
            project_type="ml_training",
            requirements=[
                "Data preprocessing",
                "Feature engineering",
                "Model training",
                "Evaluation",
            ],
            constraints=["Must use Python", "Should be deployable"],
        )

        print("Complete workflow created successfully!")
        print(f"Plan: {result['plan'].summary}")
        print(
            f"Workflow Structure: {len(result['workflow'].nodes)} nodes, {len(result['workflow'].edges)} edges"
        )
        print(f"Mermaid Chart: {result['mermaid_chart'].description}")

    finally:
        db.close()


async def example_agent_call_monitoring(user_id: uuid.UUID, project_id: uuid.UUID):
    """Example of monitoring agent calls and responses using the WorkflowAgent"""

    # Initialize settings
    settings = APISettings(
        api_model_provider="mistral",
        api_model_name="mistral:mistral-large-latest",
        api_model_key="your_mistral_api_key_here",
    )

    # Create database session
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Create the workflow agent
        agent = WorkflowAgent(settings)

        print("=== Agent Call Monitoring ===")

        # Get agent call summary
        call_summary = agent.get_agent_call_summary(db, project_id)
        if call_summary["exists"]:
            print(f"Total Agent Calls: {call_summary['total_calls']}")
            print(f"Successful Calls: {call_summary['successful_calls']}")
            print(f"Failed Calls: {call_summary['failed_calls']}")
            print(f"Success Rate: {call_summary['success_rate']:.1f}%")
            print(f"First Call: {call_summary['first_call']}")
            print(f"Last Call: {call_summary['last_call']}")

            print("\nRecent Agent Calls:")
            for call in call_summary["recent_calls"]:
                status = "❌ ERROR" if call["is_error"] else "✅ SUCCESS"
                print(f"{status} - {call['created_at']}")
                print(f"  Prompt: {call['prompt_preview']}")
                print(f"  Response: {call['response_preview']}")
                print()
        else:
            print("No agent calls found for this project")

        # Get detailed agent call history
        print("=== Detailed Agent Call History ===")
        agent_calls = agent.get_project_agent_calls(db, project_id, limit=5)
        for call in agent_calls:
            print(f"Call ID: {call.id}")
            print(f"Created: {call.created_at}")
            print(f"Prompt: {call.prompt[:200]}...")
            print(f"Response: {call.response[:200]}...")
            print("-" * 50)

    finally:
        db.close()


if __name__ == "__main__":
    # Run examples
    print("=== Example 1: Create Plan ===")
    user_id, project_id = asyncio.run(example_create_plan())

    print("\n=== Example 2: Edit Plan ===")
    asyncio.run(example_edit_plan(user_id, project_id))

    print("\n=== Example 3: Translate Plan to Workflow ===")
    asyncio.run(example_translate_plan_to_workflow(user_id, project_id))

    print("\n=== Example 4: Monitor Agent Calls ===")
    asyncio.run(example_agent_call_monitoring(user_id, project_id))

    print("\n=== Example 5: Create Complete Workflow ===")
    asyncio.run(example_create_complete_workflow())
