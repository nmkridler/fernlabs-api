#!/usr/bin/env python3
"""
Test script to verify WaitForUserInput functionality
"""

import asyncio
import sys
import os
from unittest.mock import Mock, MagicMock

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from fernlabs_api.workflow.generator import (
        WorkflowAgent,
        WorkflowState,
        WorkflowDependencies,
        WaitForUserInput,
    )
    from fernlabs_api.settings import APISettings

    print("✅ Successfully imported workflow modules")

    async def test_wait_for_user_input():
        """Test the WaitForUserInput node functionality"""

        # Mock settings
        settings = APISettings(
            api_model_name="test-model",
            api_model_provider="openai",
            api_model_key="test-key",
        )

        # Mock database session
        mock_db = Mock()
        mock_project = Mock()
        mock_project.status = "needs_input"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project
        mock_db.commit.return_value = None
        mock_db.add.return_value = None

        # Create workflow agent
        agent = WorkflowAgent(settings)

        print("✅ Created WorkflowAgent instance")

        # Test 1: No user response - should pause workflow
        print("\n=== Test 1: No user response ===")
        state = WorkflowState(
            user_id="test-user-id",
            project_id="test-project-id",
            chat_history=[{"role": "user", "content": "Test message"}],
            followup_question="What is your budget?",
            user_response=None,
            db=mock_db,
        )

        deps = WorkflowDependencies(settings=settings, db=mock_db)

        # Create WaitForUserInput node
        wait_node = WaitForUserInput()

        # Mock the GraphRunContext
        mock_ctx = Mock()
        mock_ctx.state = state
        mock_ctx.deps = deps

        try:
            result = await wait_node.run(mock_ctx)
            print(f"✅ WaitForUserInput.run() returned: {result}")
            print(f"✅ Node type: {type(result).__name__}")

            # Check if it's an End node with waiting_for_input status
            if hasattr(result, "data") and isinstance(result.data, dict):
                print(f"✅ End data: {result.data}")
                if result.data.get("status") == "waiting_for_input":
                    print("✅ Correctly paused workflow with waiting_for_input status")
                else:
                    print("⚠️  End data doesn't have expected waiting_for_input status")
            else:
                print("⚠️  Result is not an End node with data")

        except Exception as e:
            print(f"❌ Error running WaitForUserInput: {e}")

        # Test 2: With user response - should proceed to EditPlan
        print("\n=== Test 2: With user response ===")
        state.user_response = "My budget is $10,000"

        try:
            result = await wait_node.run(mock_ctx)
            print(f"✅ WaitForUserInput.run() returned: {result}")
            print(f"✅ Node type: {type(result).__name__}")

            # Check if it's proceeding to EditPlan
            if "EditPlan" in str(type(result)):
                print("✅ Correctly proceeding to EditPlan with user response")
            else:
                print("⚠️  Not proceeding to EditPlan as expected")

        except Exception as e:
            print(f"❌ Error running WaitForUserInput: {e}")

        print("\n🎉 WaitForUserInput tests completed!")

        # Test workflow resumption
        print("\n=== Test 3: Workflow resumption ===")
        try:
            result = await agent.resume_workflow(
                user_id="test-user-id",
                project_id="test-project-id",
                chat_history=[{"role": "user", "content": "Test message"}],
                db=mock_db,
                user_response="My budget is $10,000",
            )
            print(f"✅ Resume workflow result: {result}")
        except Exception as e:
            print(
                f"⚠️  Resume workflow test had issues (expected without real API keys): {e}"
            )

    # Run the test
    if __name__ == "__main__":
        asyncio.run(test_wait_for_user_input())

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the fernlabs-api directory")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
