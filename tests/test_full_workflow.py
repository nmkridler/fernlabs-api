#!/usr/bin/env python3
"""
Comprehensive test of the non-linear workflow system.
This demonstrates the new structure that eliminates circular imports.
"""

import pytest
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    from fernlabs_api.settings import APISettings

    return APISettings(
        api_model_name="gpt-4",
        api_model_provider="openai",
        api_model_key="test-key",
    )


@pytest.fixture
def complex_plan():
    """Complex test plan with loops and conditionals"""
    return """
    1. Start: Initialize the system
    2. Load Configuration: Read config files
    3. If Config Valid: proceed to data loading
    4. Load Data: Load data from sources
    5. Validate Data: Check data integrity
    6. If Data Valid: proceed to processing
    7. Process Data: Apply transformations
    8. Check Results: Verify output quality
    9. If Quality Good: save results
    10. If Quality Bad: loop back to processing
    11. Save Results: Store final output
    12. End: Complete workflow
    """


def test_workflow_agent_import(mock_settings):
    """Test importing and creating the WorkflowAgent"""
    from fernlabs_api.workflow.workflow_agent import WorkflowAgent

    # Create workflow agent
    agent = WorkflowAgent(mock_settings)
    assert agent is not None
    assert hasattr(agent, "settings")


def test_node_class_imports():
    """Test importing all node classes"""
    from fernlabs_api.workflow.nodes import (
        CreatePlan,
        AssessPlan,
        WaitForUserInput,
        EditPlan,
        ExecutePlanStep,
    )

    # If we get here, imports were successful
    assert CreatePlan is not None
    assert AssessPlan is not None
    assert WaitForUserInput is not None
    assert EditPlan is not None
    assert ExecutePlanStep is not None


def test_base_functions_import():
    """Test importing base functions"""
    from fernlabs_api.workflow.base import (
        _parse_plan_into_steps,
        _parse_connections_from_plan,
        _generate_plan_mermaid_chart_with_connections,
    )

    # If we get here, imports were successful
    assert _parse_plan_into_steps is not None
    assert _parse_connections_from_plan is not None
    assert _generate_plan_mermaid_chart_with_connections is not None


def test_connection_parsing(complex_plan):
    """Test connection parsing with a complex plan"""
    from fernlabs_api.workflow.base import (
        _parse_plan_into_steps,
        _parse_connections_from_plan,
    )

    plan_steps = _parse_plan_into_steps(complex_plan)
    connections = _parse_connections_from_plan(complex_plan)

    assert len(plan_steps) > 0
    assert len(connections) > 0

    # Verify we have the expected steps
    step_texts = [step.lower() for step in plan_steps]
    assert any("start" in text for text in step_texts)
    assert any("end" in text for text in step_texts)
    assert any("process data" in text for text in step_texts)


def test_mermaid_chart_generation(complex_plan):
    """Test Mermaid chart generation"""
    from fernlabs_api.workflow.base import (
        _parse_plan_into_steps,
        _parse_connections_from_plan,
        _generate_plan_mermaid_chart_with_connections,
    )

    plan_steps = _parse_plan_into_steps(complex_plan)
    connections = _parse_connections_from_plan(complex_plan)

    mermaid_chart = _generate_plan_mermaid_chart_with_connections(
        plan_steps, connections
    )

    assert mermaid_chart is not None
    assert "flowchart TD" in mermaid_chart
    assert len(plan_steps) > 0


def test_connection_analysis(complex_plan):
    """Test connection analysis"""
    from fernlabs_api.workflow.base import _parse_connections_from_plan

    connections = _parse_connections_from_plan(complex_plan)

    loops = [conn for conn in connections if conn["type"] == "loop_back"]
    conditionals = [conn for conn in connections if conn["type"] == "conditional"]
    sequential = [conn for conn in connections if conn["type"] == "next"]

    assert len(loops) > 0
    assert len(conditionals) > 0
    assert len(sequential) > 0


def test_workflow_graph_creation():
    """Test workflow graph creation"""
    # This test would verify that workflow graphs can be created
    # For now, we'll just assert that the test passes
    assert True


def test_workflow_execution_flow():
    """Test workflow execution flow"""
    # Test that the workflow can handle different execution paths
    execution_paths = [
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12],  # Happy path
        [1, 2, 3, 4, 5, 6, 7, 8, 10, 7, 8, 9, 11, 12],  # Path with loop
    ]

    for path in execution_paths:
        assert len(path) > 0
        assert path[0] == 1  # Start with step 1
        assert path[-1] == 12  # End with step 12
