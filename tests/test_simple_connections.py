#!/usr/bin/env python3
"""
Simple test for connection parsing and Mermaid generation.
This tests the core functionality without importing the entire workflow system.
"""

import pytest
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


def test_workflow_functions_import():
    """Test that workflow functions can be imported"""
    try:
        from fernlabs_api.workflow.base import (
            _parse_connections_from_plan,
            _parse_plan_into_steps,
        )
        from fernlabs_api.workflow.base import (
            _generate_plan_mermaid_chart_with_connections,
        )

        # If we get here, imports were successful
        assert _parse_connections_from_plan is not None
        assert _parse_plan_into_steps is not None
        assert _generate_plan_mermaid_chart_with_connections is not None

    except ImportError as e:
        pytest.fail(f"Import error: {e}")


def test_plan_parsing(test_plan):
    """Test the connection parsing logic"""
    from fernlabs_api.workflow.base import (
        _parse_connections_from_plan,
        _parse_plan_into_steps,
    )

    # Parse the plan to extract connections
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


def test_connection_structure(test_plan):
    """Test connection structure and properties"""
    from fernlabs_api.workflow.base import _parse_connections_from_plan

    connections = _parse_connections_from_plan(test_plan)

    for conn in connections:
        assert "source" in conn
        assert "target" in conn
        assert "type" in conn
        assert isinstance(conn["source"], int)
        assert isinstance(conn["target"], int)
        assert isinstance(conn["type"], str)


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


def test_connection_analysis(test_plan):
    """Test connection analysis and categorization"""
    from fernlabs_api.workflow.base import _parse_connections_from_plan

    connections = _parse_connections_from_plan(test_plan)

    # Find loops
    loops = [conn for conn in connections if conn["type"] == "loop_back"]
    assert len(loops) > 0

    for loop in loops:
        assert loop["source"] > loop["target"]  # Loop should go back to earlier step

    # Find conditionals
    conditionals = [conn for conn in connections if conn["type"] == "conditional"]
    assert len(conditionals) > 0

    # Find sequential connections
    sequential = [conn for conn in connections if conn["type"] == "next"]
    assert len(sequential) > 0


def test_connection_labels_and_conditions(test_plan):
    """Test that connections have proper labels and conditions"""
    from fernlabs_api.workflow.base import _parse_connections_from_plan

    connections = _parse_connections_from_plan(test_plan)

    # Check that conditional connections have labels
    conditional_connections = [
        conn for conn in connections if conn["type"] == "conditional"
    ]

    for conn in conditional_connections:
        if conn.get("label"):
            assert isinstance(conn["label"], str)
            assert len(conn["label"]) > 0


def test_plan_step_numbering(test_plan):
    """Test that plan steps have proper numbering"""
    from fernlabs_api.workflow.base import _parse_plan_into_steps

    plan_steps = _parse_plan_into_steps(test_plan)

    # Check that steps start with numbers
    for step in plan_steps:
        if step.strip():
            assert step[0].isdigit(), f"Step should start with a number: {step}"


def test_connection_validation(test_plan):
    """Test that connections are valid"""
    from fernlabs_api.workflow.base import _parse_connections_from_plan

    connections = _parse_connections_from_plan(test_plan)

    for conn in connections:
        # Source and target should be positive integers
        assert conn["source"] > 0
        assert conn["target"] > 0

        # Connection type should be valid
        valid_types = ["next", "conditional", "loop_back"]
        assert conn["type"] in valid_types
