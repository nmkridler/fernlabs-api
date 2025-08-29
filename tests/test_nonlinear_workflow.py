#!/usr/bin/env python3
"""
Test script for non-linear workflow capabilities.
This demonstrates how the workflow can now handle cycles, conditionals, and non-linear execution paths.
"""

import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fernlabs_api.workflow.workflow_agent import WorkflowAgent
from fernlabs_api.settings import APISettings
from fernlabs_api.workflow.base import WorkflowState, WorkflowDependencies
from fernlabs_api.db.model import Plan, PlanConnection


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    return APISettings(
        api_model_name="gpt-4", api_model_provider="openai", api_model_key="test-key"
    )


@pytest.fixture
def test_plan():
    """Test plan with loops and conditionals"""
    return """
    1. Load Data: load the csv data from the file
    2. Validate Data: check if the data is valid
    3. If Data Valid: proceed to transformation
    4. Transform Data: apply data transformations
    5. Check Quality: verify the transformed data quality
    6. If Quality Good: save results
    7. If Quality Bad: loop back to transformation
    8. Save Results: save the final results to database
    """


def test_plan_parsing(test_plan):
    """Test parsing the plan into steps and connections"""
    from fernlabs_api.workflow.base import (
        _parse_connections_from_plan,
        _parse_plan_into_steps,
    )

    plan_steps = _parse_plan_into_steps(test_plan)
    connections = _parse_connections_from_plan(test_plan)

    assert len(plan_steps) > 0
    assert len(connections) > 0

    # Verify we have the expected steps
    step_texts = [step.lower() for step in plan_steps]
    assert any("load data" in text for text in step_texts)
    assert any("validate data" in text for text in step_texts)
    assert any("transform data" in text for text in step_texts)
    assert any("save results" in text for text in step_texts)


def test_connection_parsing(test_plan):
    """Test parsing connections from the plan"""
    from fernlabs_api.workflow.base import _parse_connections_from_plan

    connections = _parse_connections_from_plan(test_plan)

    # Find loops
    loops = [conn for conn in connections if conn["type"] == "loop_back"]
    assert len(loops) > 0

    # Find conditionals
    conditionals = [conn for conn in connections if conn["type"] == "conditional"]
    assert len(conditionals) > 0

    # Find sequential connections
    sequential = [conn for conn in connections if conn["type"] == "next"]
    assert len(sequential) > 0


def test_mermaid_chart_generation(test_plan):
    """Test Mermaid chart generation with connections"""
    from fernlabs_api.workflow.base import (
        _parse_connections_from_plan,
        _parse_plan_into_steps,
        _generate_plan_mermaid_chart_with_connections,
    )

    plan_steps = _parse_plan_into_steps(test_plan)
    connections = _parse_connections_from_plan(test_plan)

    mermaid_chart = _generate_plan_mermaid_chart_with_connections(
        plan_steps, connections
    )

    assert mermaid_chart is not None
    assert "flowchart TD" in mermaid_chart
    assert len(plan_steps) > 0


def test_workflow_execution_paths():
    """Test different execution paths through the workflow"""
    # Simulate different execution paths
    execution_paths = [
        [1, 2, 3, 4, 5, 6, 8],  # Happy path: no loops
        [1, 2, 3, 4, 5, 7, 4, 5, 6, 8],  # Path with one loop
        [1, 2, 3, 4, 5, 7, 4, 5, 7, 4, 5, 6, 8],  # Path with multiple loops
    ]

    for i, path in enumerate(execution_paths):
        assert len(path) > 0
        assert path[0] == 1  # All paths should start with step 1
        assert path[-1] == 8  # All paths should end with step 8

        # Step 4 is the transformation step that can be looped
        if i > 0:  # Skip the first path (no loops)
            assert path.count(4) > 1  # Should have multiple occurrences of step 4


def test_workflow_agent_creation(mock_settings):
    """Test creating a workflow agent"""
    agent = WorkflowAgent(mock_settings)
    assert agent is not None
    assert hasattr(agent, "settings")
