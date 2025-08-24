"""
Shared pytest fixtures and configuration for fernlabs-api tests

This file provides common fixtures that can be used across all test modules.
"""

import pytest
import uuid
import sys
import os
from unittest.mock import Mock, AsyncMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fernlabs_api.settings import APISettings
from fernlabs_api.workflow.generator import PlanResponse

# Patch the provider factory at module level for testing
from unittest.mock import patch
from fernlabs_api.workflow.generator import _provider_factory


def mock_provider_factory(provider_name: str, api_key: str):
    """Mock provider factory for testing"""
    from unittest.mock import Mock

    mock_provider = Mock()
    mock_provider.__class__.__name__ = "MockProvider"
    return mock_provider


# Apply the patch
patcher = patch(
    "fernlabs_api.workflow.generator._provider_factory", mock_provider_factory
)
patcher.start()


class MockDatabaseSession:
    """Mock database session for testing"""

    def __init__(self):
        self.data = {
            "plans": [],
            "workflows": [],
            "agent_calls": [],
            "projects": [],
            "users": [],
        }
        self.committed = False

    def add(self, obj):
        if hasattr(obj, "__tablename__"):
            table_name = obj.__tablename__
            if table_name in self.data:
                # Generate a mock ID if not present
                if not hasattr(obj, "id") or obj.id is None:
                    obj.id = uuid.uuid4()
                self.data[table_name].append(obj)

    def commit(self):
        self.committed = True

    def query(self, model_class):
        return MockQuery(self.data.get(model_class.__tablename__, []))

    def filter(self, *args):
        return self

    def first(self):
        return None


class MockQuery:
    """Mock query object for testing"""

    def __init__(self, data):
        self.data = data

    def filter(self, *args):
        return self

    def order_by(self, field):
        return self

    def limit(self, limit):
        return self

    def all(self):
        return self.data

    def first(self):
        return self.data[0] if self.data else None


class MockAIResponse:
    """Mock AI response for testing"""

    def __init__(self, output):
        self.output = output


@pytest.fixture(scope="session")
def test_user_id():
    """Fixture providing a test user ID (session-scoped)"""
    return uuid.uuid4()


@pytest.fixture(scope="session")
def test_project_id():
    """Fixture providing a test project ID (session-scoped)"""
    return uuid.uuid4()


@pytest.fixture
def test_chat_history():
    """Fixture providing test chat history"""
    return [
        {"role": "user", "content": "I want to create a data processing workflow"},
        {
            "role": "assistant",
            "content": "I can help you with that. What kind of data are you processing?",
        },
    ]


@pytest.fixture
def test_settings():
    """Fixture providing test API settings"""
    return APISettings(
        api_model_provider="mock",
        api_model_name="mock:test-model",
        api_model_key="mock-key",
    )


@pytest.fixture
def mock_db():
    """Fixture providing a mock database session"""
    return MockDatabaseSession()


@pytest.fixture
def mock_ai_response():
    """Fixture providing a mock AI response"""
    return MockAIResponse(
        PlanResponse(
            plan="1. Data Collection\n2. Data Cleaning\n3. Data Processing\n4. Results Analysis",
            summary="A comprehensive data processing workflow",
            key_phases=["Collection", "Cleaning", "Processing", "Analysis"],
            estimated_duration="2-3 weeks",
        )
    )


@pytest.fixture
def mock_provider():
    """Fixture providing a mock provider for testing"""
    mock_provider = Mock()
    mock_provider.__class__.__name__ = "MockProvider"
    return mock_provider


@pytest.fixture
def mock_workflow_agent(test_settings):
    """Fixture providing a WorkflowAgent with mocked AI"""
    with patch("fernlabs_api.workflow.generator.Agent") as mock_agent_class:
        mock_agent = Mock()
        mock_agent.run = AsyncMock()

        # Mock the tools
        mock_agent.tool = Mock()

        # Mock agent responses
        mock_agent.run.return_value = MockAIResponse(
            PlanResponse(
                plan="1. Data Collection\n2. Data Cleaning\n3. Data Processing\n4. Results Analysis",
                summary="A comprehensive data processing workflow",
                key_phases=["Collection", "Cleaning", "Processing", "Analysis"],
                estimated_duration="2-3 weeks",
            )
        )

        mock_agent_class.return_value = mock_agent

        from fernlabs_api.workflow.generator import WorkflowAgent

        return WorkflowAgent(test_settings)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line(
        "markers", "asyncio: mark test as requiring asyncio support"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names"""
    for item in items:
        # Mark async tests
        if "async" in item.name.lower() or (
            item.cls and "async" in item.cls.__name__.lower()
        ):
            item.add_marker(pytest.mark.asyncio)

        # Mark unit tests (default)
        if not any(
            marker.name in ["integration", "slow"] for marker in item.iter_markers()
        ):
            item.add_marker(pytest.mark.unit)
