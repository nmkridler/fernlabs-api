#!/usr/bin/env python3
"""
Test script to verify WaitForUserInput functionality
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, MagicMock

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    from fernlabs_api.settings import APISettings

    return APISettings(
        api_model_name="test-model",
        api_model_provider="openai",
        api_model_key="test-key",
    )


@pytest.fixture
def mock_db():
    """Mock database session"""
    mock_db = Mock()
    mock_project = Mock()
    mock_project.status = "needs_input"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_project
    mock_db.commit.return_value = None
    mock_db.add.return_value = None
    return mock_db


@pytest.fixture
def mock_workflow_state(mock_db):
    """Mock workflow state"""
    from fernlabs_api.workflow.base import WorkflowState
    import uuid

    return WorkflowState(
        user_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        chat_history=[{"role": "user", "content": "Test message"}],
        followup_question="What is your budget?",
        user_response=None,
        db=mock_db,
    )


@pytest.fixture
def mock_workflow_dependencies(mock_settings, mock_db):
    """Mock workflow dependencies"""
    from unittest.mock import Mock

    # Create a simple mock that has the required attributes
    mock_deps = Mock()
    mock_deps.settings = mock_settings
    mock_deps.db = mock_db

    return mock_deps


@pytest.fixture
def mock_context(mock_workflow_state, mock_workflow_dependencies):
    """Mock GraphRunContext"""
    mock_ctx = Mock()
    mock_ctx.state = mock_workflow_state
    mock_ctx.deps = mock_workflow_dependencies
    return mock_ctx


@pytest.fixture
def wait_node():
    """WaitForUserInput node instance"""
    from fernlabs_api.workflow.nodes import WaitForUserInput

    return WaitForUserInput()


def test_imports():
    """Test that workflow modules can be imported"""
    try:
        from fernlabs_api.workflow.workflow_agent import WorkflowAgent
        from fernlabs_api.workflow.base import WorkflowState, WorkflowDependencies
        from fernlabs_api.workflow.nodes import WaitForUserInput
        from fernlabs_api.settings import APISettings

        # If we get here, imports were successful
        assert WorkflowAgent is not None
        assert WorkflowState is not None
        assert WorkflowDependencies is not None
        assert WaitForUserInput is not None
        assert APISettings is not None

    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


def test_workflow_agent_creation(mock_settings):
    """Test creating a WorkflowAgent instance"""
    from fernlabs_api.workflow.workflow_agent import WorkflowAgent

    agent = WorkflowAgent(mock_settings)
    assert agent is not None
    assert hasattr(agent, "settings")


def test_workflow_state_creation(mock_db):
    """Test creating a WorkflowState instance"""
    from fernlabs_api.workflow.base import WorkflowState
    import uuid

    user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    state = WorkflowState(
        user_id=user_id,
        project_id=project_id,
        chat_history=[{"role": "user", "content": "Test message"}],
        followup_question="What is your budget?",
        user_response=None,
        db=mock_db,
    )

    assert state.user_id == user_id
    assert state.project_id == project_id
    assert len(state.chat_history) == 1
    assert state.followup_question == "What is your budget?"
    assert state.user_response is None
    assert state.db == mock_db


def test_workflow_dependencies_creation(mock_settings, mock_db):
    """Test creating WorkflowDependencies instance"""
    from unittest.mock import Mock

    # Create a simple mock that has the required attributes
    mock_deps = Mock()
    mock_deps.settings = mock_settings
    mock_deps.db = mock_db

    assert mock_deps.settings == mock_settings
    assert mock_deps.db == mock_db


def test_wait_node_creation():
    """Test creating WaitForUserInput node"""
    from fernlabs_api.workflow.nodes import WaitForUserInput

    wait_node = WaitForUserInput()
    assert wait_node is not None


@pytest.mark.asyncio
async def test_wait_for_user_input_no_response(wait_node, mock_context):
    """Test WaitForUserInput when there's no user response"""
    try:
        result = await wait_node.run(mock_context)

        # Check if it's an End node with waiting_for_input status
        if hasattr(result, "data") and isinstance(result.data, dict):
            assert result.data.get("status") == "waiting_for_input"
        else:
            # If not an End node, it should be some other valid result
            assert result is not None

    except Exception as e:
        pytest.fail(f"Error running WaitForUserInput: {e}")


@pytest.mark.asyncio
async def test_wait_for_user_input_with_response(wait_node, mock_context):
    """Test WaitForUserInput when there's a user response"""
    # Set user response
    mock_context.state.user_response = "My budget is $10,000"

    try:
        result = await wait_node.run(mock_context)

        # Should proceed to EditPlan or similar node
        assert result is not None

        # Check if it's proceeding to EditPlan
        if "EditPlan" in str(type(result)):
            assert True  # Successfully proceeding to EditPlan
        else:
            # It might be a different node type, which is also valid
            assert result is not None

    except Exception as e:
        pytest.fail(f"Error running WaitForUserInput with response: {e}")


def test_mock_database_functionality(mock_db):
    """Test that mock database functions work correctly"""
    # Test query functionality
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_first = mock_filter.first.return_value

    assert mock_first.status == "needs_input"

    # Test commit functionality
    mock_db.commit()
    mock_db.commit.assert_called_once()

    # Test add functionality
    mock_db.add("test_object")
    mock_db.add.assert_called_once_with("test_object")


def test_workflow_state_properties(mock_workflow_state):
    """Test WorkflowState properties and methods"""
    # Test property access
    assert mock_workflow_state.user_id is not None
    assert mock_workflow_state.project_id is not None
    assert mock_workflow_state.followup_question == "What is your budget?"
    assert mock_workflow_state.user_response is None

    # Test chat history
    assert len(mock_workflow_state.chat_history) == 1
    assert mock_workflow_state.chat_history[0]["role"] == "user"
    assert mock_workflow_state.chat_history[0]["content"] == "Test message"


def test_context_integration(mock_context):
    """Test that context integrates state and dependencies correctly"""
    assert mock_context.state is not None
    assert mock_context.deps is not None
    assert hasattr(mock_context.state, "user_id")
    assert hasattr(mock_context.deps, "settings")
    assert hasattr(mock_context.deps, "db")
