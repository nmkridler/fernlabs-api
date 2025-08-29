#!/usr/bin/env python3
"""
Direct import test for connection parsing functions.
This bypasses the workflow system to test the core functionality.
"""

import pytest
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def test_plan():
    """Test plan for connection parsing"""
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


def test_direct_imports():
    """Test importing functions directly from their modules"""
    try:
        # Import the base module directly
        import fernlabs_api.workflow.base as base

        # If we get here, import was successful
        assert base is not None

    except Exception as e:
        pytest.fail(f"Import error: {e}")


def test_base_module_functions(test_plan):
    """Test the functions directly from the base module"""
    import fernlabs_api.workflow.base as base

    # Test the functions directly
    plan_steps = base._parse_plan_into_steps(test_plan)
    connections = base._parse_connections_from_plan(test_plan)

    assert len(plan_steps) > 0
    assert len(connections) > 0

    # Verify we have the expected steps
    step_texts = [step.lower() for step in plan_steps]
    assert any("load data" in text for text in step_texts)
    assert any("validate data" in text for text in step_texts)
    assert any("transform data" in text for text in step_texts)
    assert any("save results" in text for text in step_texts)


def test_plan_step_parsing(test_plan):
    """Test plan step parsing functionality"""
    import fernlabs_api.workflow.base as base

    plan_steps = base._parse_plan_into_steps(test_plan)

    # Check that steps are properly parsed
    assert len(plan_steps) == 8  # Should have 8 steps

    # Check that steps start with numbers
    for i, step in enumerate(plan_steps, 1):
        if step.strip():
            assert step[0].isdigit(), f"Step {i} should start with a number: {step}"

            # Check step numbering
            step_num = int(step.split(".")[0])
            assert step_num == i, f"Step {i} should have number {i}: {step}"


def test_connection_parsing(test_plan):
    """Test connection parsing functionality"""
    import fernlabs_api.workflow.base as base

    connections = base._parse_connections_from_plan(test_plan)

    # Check connection structure
    for conn in connections:
        assert "source" in conn
        assert "target" in conn
        assert "type" in conn
        assert isinstance(conn["source"], int)
        assert isinstance(conn["target"], int)
        assert isinstance(conn["type"], str)

    # Check that we have the expected connection types
    connection_types = [conn["type"] for conn in connections]
    assert "next" in connection_types
    assert "conditional" in connection_types
    assert "loop_back" in connection_types


def test_mermaid_chart_generation(test_plan):
    """Test Mermaid chart generation"""
    import fernlabs_api.workflow.base as base

    plan_steps = base._parse_plan_into_steps(test_plan)
    connections = base._parse_connections_from_plan(test_plan)

    # Test Mermaid chart generation
    mermaid_chart = base._generate_plan_mermaid_chart_with_connections(
        plan_steps, connections
    )

    assert mermaid_chart is not None
    assert isinstance(mermaid_chart, str)
    assert "flowchart TD" in mermaid_chart
    assert len(mermaid_chart) > 0


def test_connection_analysis(test_plan):
    """Test connection analysis and categorization"""
    import fernlabs_api.workflow.base as base

    connections = base._parse_connections_from_plan(test_plan)

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


def test_connection_metadata(test_plan):
    """Test connection metadata like conditions and labels"""
    import fernlabs_api.workflow.base as base

    connections = base._parse_connections_from_plan(test_plan)

    for conn in connections:
        # Check optional fields if they exist
        if conn.get("condition"):
            assert isinstance(conn["condition"], str)
            assert len(conn["condition"]) > 0

        if conn.get("label"):
            assert isinstance(conn["label"], str)
            assert len(conn["label"]) > 0


def test_plan_validation(test_plan):
    """Test plan validation and structure"""
    import fernlabs_api.workflow.base as base

    plan_steps = base._parse_plan_into_steps(test_plan)
    connections = base._parse_connections_from_plan(test_plan)

    # Test that plan has valid structure
    assert len(plan_steps) > 0
    assert len(connections) > 0

    # Test that connections reference valid steps
    for conn in connections:
        assert 1 <= conn["source"] <= len(plan_steps)
        assert 1 <= conn["target"] <= len(plan_steps)


def test_function_signatures():
    """Test that functions have the expected signatures"""
    import fernlabs_api.workflow.base as base
    import inspect

    # Test _parse_plan_into_steps signature
    parse_steps_sig = inspect.signature(base._parse_plan_into_steps)
    assert len(parse_steps_sig.parameters) == 1  # Should take one parameter

    # Test _parse_connections_from_plan signature
    parse_conn_sig = inspect.signature(base._parse_connections_from_plan)
    assert len(parse_conn_sig.parameters) == 1  # Should take one parameter

    # Test _generate_plan_mermaid_chart_with_connections signature
    mermaid_sig = inspect.signature(base._generate_plan_mermaid_chart_with_connections)
    assert len(mermaid_sig.parameters) == 2  # Should take two parameters
