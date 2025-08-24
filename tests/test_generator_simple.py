#!/usr/bin/env python3
"""
Simple pytest-based tests for the WorkflowAgent functionality in generator.py

This module tests basic functionality without complex mocking or AI integration.
"""

import pytest
import uuid
import sys
import os
from typing import Dict, Any

# Add the project root to the Python path (go up one level from tests/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fernlabs_api.settings import APISettings
from fernlabs_api.workflow.generator import (
    WorkflowAgent,
    PlanDependencies,
    PlanResponse,
)
from fernlabs_api.db.model import Plan, Workflow, AgentCall, Project, User


def test_imports():
    """Test that all required modules can be imported"""
    # This test is implicit - if we get here, imports succeeded
    assert True


def test_settings_validation():
    """Test that settings can be created and validated"""
    # Test default settings
    settings = APISettings()
    assert settings.api_model_provider == "mistral"

    # Test custom settings
    custom_settings = APISettings(
        api_model_provider="openai",
        api_model_name="gpt-4",
        api_model_key="test-key",
    )
    assert custom_settings.api_model_provider == "openai"
    assert custom_settings.api_model_name == "gpt-4"


def test_plan_dependencies_creation(test_user_id, test_project_id, test_chat_history):
    """Test that PlanDependencies model can be created"""
    deps = PlanDependencies(
        user_id=test_user_id,
        project_id=test_project_id,
        chat_history=test_chat_history,
        db=None,  # We'll set this to None for testing
    )

    assert deps.user_id == test_user_id
    assert deps.project_id == test_project_id
    assert len(deps.chat_history) == 2
    assert deps.db is None


def test_plan_response_model():
    """Test that PlanResponse model can be created"""
    response = PlanResponse(
        plan="Test plan content",
        summary="Test summary",
        key_phases=["Phase 1", "Phase 2"],
        estimated_duration="1 week",
    )

    assert response.plan == "Test plan content"
    assert response.summary == "Test summary"
    assert len(response.key_phases) == 2
    assert response.estimated_duration == "1 week"


def test_plan_parsing(mock_workflow_agent):
    """Test the plan parsing functionality"""
    test_cases = [
        ("1. First step\n2. Second step\n3. Third step", 3),
        ("• Start\n• Process\n• End", 3),
        ("Phase 1: Planning\n1. Define scope\n2. Set timeline", 3),
        ("Phase 1: Planning\n1. Define scope\n2. Set timeline\nPhase 2: Execution", 4),
        ("This is step one.\n\nThis is step two.\n\nThis is step three.", 3),
    ]

    for plan_text, expected_steps in test_cases:
        steps = mock_workflow_agent._parse_plan_into_steps(plan_text)
        assert len(steps) == expected_steps, (
            f"Expected {expected_steps} steps for: {plan_text[:50]}..."
        )


def test_mermaid_generation(mock_workflow_agent):
    """Test Mermaid chart generation"""
    workflow_data = {
        "nodes": [
            {"id": "A", "name": "Start", "type": "start"},
            {"id": "B", "name": "Process", "type": "task"},
            {"id": "C", "name": "End", "type": "end"},
        ],
        "edges": [
            {"source": "A", "target": "B", "label": "Next"},
            {"source": "B", "target": "C", "label": "Complete"},
        ],
    }

    mermaid_chart = mock_workflow_agent.generate_mermaid_from_workflow(workflow_data)

    # Check that the chart contains expected elements
    assert "flowchart TD" in mermaid_chart
    assert "A([ Start ])" in mermaid_chart
    assert "B[ Process ]" in mermaid_chart
    assert "C([ End ])" in mermaid_chart
    assert "A -->|Next| B" in mermaid_chart
    assert "B -->|Complete| C" in mermaid_chart


def test_mermaid_generation_with_decision_nodes(mock_workflow_agent):
    """Test Mermaid chart generation with decision nodes"""
    workflow_data = {
        "nodes": [
            {"id": "A", "name": "Start", "type": "start"},
            {"id": "B", "name": "Decision", "type": "decision"},
            {"id": "C", "name": "Process", "type": "task"},
            {"id": "D", "name": "End", "type": "end"},
        ],
        "edges": [
            {"source": "A", "target": "B", "label": "Next"},
            {"source": "B", "target": "C", "label": "Yes"},
            {"source": "B", "target": "D", "label": "No"},
            {"source": "C", "target": "D", "label": "Complete"},
        ],
    }

    mermaid_chart = mock_workflow_agent.generate_mermaid_from_workflow(workflow_data)

    # Check that decision nodes are properly formatted
    assert "B{ Decision }" in mermaid_chart
    assert "A -->|Next| B" in mermaid_chart
    assert "B -->|Yes| C" in mermaid_chart
    assert "B -->|No| D" in mermaid_chart


def test_error_handling(mock_workflow_agent):
    """Test error handling in Mermaid generation"""
    # Test with invalid data
    invalid_data = {"invalid": "data"}
    mermaid_chart = mock_workflow_agent.generate_mermaid_from_workflow(invalid_data)

    # Should return a fallback chart
    assert "flowchart TD" in mermaid_chart
    assert "Error" in mermaid_chart or "No nodes found" in mermaid_chart


def test_error_handling_empty_nodes(mock_workflow_agent):
    """Test error handling with empty nodes"""
    # Test with empty nodes
    empty_data = {"nodes": [], "edges": []}
    mermaid_chart = mock_workflow_agent.generate_mermaid_from_workflow(empty_data)

    # Should return a fallback chart
    assert "flowchart TD" in mermaid_chart
    assert "No nodes found" in mermaid_chart


def test_plan_parsing_edge_cases(mock_workflow_agent):
    """Test plan parsing with edge cases"""
    edge_cases = [
        ("", 0),  # Empty string
        ("Single step", 1),  # Single step without numbering
        ("1. Step\n\n2. Another step", 2),  # Steps with extra whitespace
        ("Phase 1:\n1. Step\nPhase 2:\n2. Step", 4),  # Mixed format with colons
    ]

    for plan_text, expected_steps in edge_cases:
        steps = mock_workflow_agent._parse_plan_into_steps(plan_text)
        assert len(steps) == expected_steps, (
            f"Expected {expected_steps} steps for: {repr(plan_text)}"
        )


def test_workflow_agent_initialization(mock_workflow_agent):
    """Test that WorkflowAgent initializes correctly"""
    assert hasattr(mock_workflow_agent, "agent")
    assert hasattr(mock_workflow_agent, "settings")
    assert mock_workflow_agent.settings.api_model_provider == "mock"


if __name__ == "__main__":
    # Allow running with python directly for debugging
    pytest.main([__file__, "-v"])
