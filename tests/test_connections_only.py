#!/usr/bin/env python3
"""
Simple test for connection parsing and Mermaid generation.
This tests the core functionality without requiring database connections.
"""

import pytest
import sys
import os

# Add the project root to the Python path
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


def test_connection_details(test_plan):
    """Test connection details and metadata"""
    from fernlabs_api.workflow.base import _parse_connections_from_plan

    connections = _parse_connections_from_plan(test_plan)

    for conn in connections:
        # Check that source and target are valid step numbers
        assert conn["source"] > 0
        assert conn["target"] > 0

        # Check that connection type is valid
        valid_types = ["next", "conditional", "loop_back"]
        assert conn["type"] in valid_types

        # Check optional fields if they exist
        if conn.get("condition"):
            assert isinstance(conn["condition"], str)
        if conn.get("label"):
            assert isinstance(conn["label"], str)


def test_plan_step_validation(test_plan):
    """Test that plan steps are properly formatted"""
    from fernlabs_api.workflow.base import _parse_plan_into_steps

    plan_steps = _parse_plan_into_steps(test_plan)

    for step in plan_steps:
        if step.strip():
            # Steps should start with a number
            assert step[0].isdigit(), f"Step should start with a number: {step}"

            # Steps should have content after the number
            step_parts = step.split(":", 1)
            assert len(step_parts) >= 2, f"Step should have description: {step}"

            # Description should not be empty
            assert step_parts[1].strip(), (
                f"Step description should not be empty: {step}"
            )


def test_connection_consistency(test_plan):
    """Test that connections are consistent with plan steps"""
    from fernlabs_api.workflow.base import (
        _parse_connections_from_plan,
        _parse_plan_into_steps,
    )

    plan_steps = _parse_plan_into_steps(test_plan)
    connections = _parse_connections_from_plan(test_plan)

    # Get the number of steps
    num_steps = len(plan_steps)

    for conn in connections:
        # Source and target should be within valid step range
        assert 1 <= conn["source"] <= num_steps
        assert 1 <= conn["target"] <= num_steps

        # A step shouldn't connect to itself (unless it's a special case)
        if conn["type"] != "loop_back":  # Loops can go back to the same step
            assert conn["source"] != conn["target"]
