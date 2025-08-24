#!/usr/bin/env python3
"""
Comprehensive pytest-based tests for the WorkflowAgent functionality in generator.py

This module tests AI integration, database operations, and advanced functionality.
"""

import pytest
import uuid
import sys
import os
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
import logging

# Add the project root to the Python path (go up one level from tests/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fernlabs_api.settings import APISettings
from fernlabs_api.workflow.generator import (
    WorkflowAgent,
    PlanDependencies,
    PlanResponse,
)
from fernlabs_api.db.model import Plan, Workflow, AgentCall, Project, User


@pytest.fixture
def test_project(mock_db, test_user_id, test_project_id):
    """Fixture providing a test project"""
    project = Project(
        id=test_project_id,
        user_id=test_user_id,
        name="Test Data Processing Project",
        description="A test project for workflow generation",
        prompt="Create a data processing workflow",
        status="loading",
    )
    mock_db.add(project)
    return project


@pytest.fixture
def test_user(mock_db, test_user_id):
    """Fixture providing a test user"""
    user = User(id=test_user_id, email="test@example.com", name="Test User")
    mock_db.add(user)
    return user


class TestWorkflowAgent:
    """Test class for WorkflowAgent functionality"""

    def test_agent_initialization(self, mock_workflow_agent):
        """Test that the agent initializes correctly"""
        assert hasattr(mock_workflow_agent, "agent")
        assert hasattr(mock_workflow_agent, "settings")

    def test_plan_dependencies_creation(
        self, test_user_id, test_project_id, test_chat_history, mock_db
    ):
        """Test PlanDependencies model creation"""
        deps = PlanDependencies(
            user_id=test_user_id,
            project_id=test_project_id,
            chat_history=test_chat_history,
            db=mock_db,
        )

        assert deps.user_id == test_user_id
        assert deps.project_id == test_project_id
        assert len(deps.chat_history) == 2
        assert deps.db == mock_db

    def test_plan_response_model(self):
        """Test PlanResponse model creation"""
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

    def test_plan_parsing(self, mock_workflow_agent):
        """Test the plan parsing functionality"""
        test_cases = [
            ("1. First step\n2. Second step\n3. Third step", 3),
            ("• Start\n• Process\n• End", 3),
            (
                "Phase 1: Planning\n1. Define scope\n2. Set timeline\nPhase 2: Execution",
                4,
            ),
            ("This is step one.\n\nThis is step two.\n\nThis is step three.", 3),
        ]

        for plan_text, expected_steps in test_cases:
            steps = mock_workflow_agent._parse_plan_into_steps(plan_text)
            assert len(steps) == expected_steps, (
                f"Expected {expected_steps} steps for: {plan_text[:50]}..."
            )

    def test_mermaid_generation(self, mock_workflow_agent):
        """Test Mermaid chart generation"""
        workflow_data = {
            "nodes": [
                {"id": "A", "name": "Start", "type": "start"},
                {"id": "B", "name": "Process", "type": "task"},
                {"id": "C", "name": "Decision", "type": "decision"},
                {"id": "D", "name": "End", "type": "end"},
            ],
            "edges": [
                {"source": "A", "target": "B", "label": "Next"},
                {"source": "B", "target": "C", "label": "Continue"},
                {"source": "C", "target": "D", "label": "Complete"},
            ],
        }

        mermaid_chart = mock_workflow_agent.generate_mermaid_from_workflow(
            workflow_data
        )

        # Check that the chart contains expected elements
        assert "flowchart TD" in mermaid_chart
        assert "A([ Start ])" in mermaid_chart
        assert "B[ Process ]" in mermaid_chart
        assert "C{ Decision }" in mermaid_chart
        assert "D([ End ])" in mermaid_chart
        assert "A -->|Next| B" in mermaid_chart

    def test_error_handling(self, mock_workflow_agent):
        """Test error handling in Mermaid generation"""
        # Test with invalid data
        invalid_data = {"invalid": "data"}
        mermaid_chart = mock_workflow_agent.generate_mermaid_from_workflow(invalid_data)

        # Should return a fallback chart
        assert "flowchart TD" in mermaid_chart
        assert "Error" in mermaid_chart or "No nodes found" in mermaid_chart

    def test_database_operations(self, mock_workflow_agent, mock_db, test_project_id, test_user_id):
        """Test database operation methods"""
        # Create a test project first
        test_project = Project(
            id=test_project_id,
            user_id=test_user_id,
            name="Test Project",
            description="Test Description",
            prompt="Test prompt",
            status="loading",
        )
        mock_db.add(test_project)
        
        # Test project status update
        mock_workflow_agent._update_project_status(
            mock_db, test_project_id, "completed"
        )

        # Check that the project was updated
        project = mock_db.query(Project).filter().first()
        assert project.status == "completed"

        # Test existing plan retrieval
        existing_plan = mock_workflow_agent._get_existing_plan_text(
            mock_db, test_project_id, test_project_id
        )
        assert existing_plan == ""  # Should be empty initially

    def test_utility_methods(
        self, mock_workflow_agent, mock_db, test_user_id, test_project_id
    ):
        """Test utility methods"""
        # Test plan summary
        summary = mock_workflow_agent.get_plan_summary(
            mock_db, test_user_id, test_project_id
        )
        assert summary["exists"] == False  # No plan exists yet

        # Test workflow summary
        workflow_summary = mock_workflow_agent.get_workflow_summary(
            mock_db, test_user_id, test_project_id
        )
        assert workflow_summary["exists"] == False  # No workflows exist yet

        # Test agent call summary
        agent_summary = mock_workflow_agent.get_agent_call_summary(
            mock_db, test_project_id
        )
        assert agent_summary["exists"] == False  # No agent calls exist yet


class TestWorkflowAgentAsync:
    """Test class for async WorkflowAgent functionality"""

    @pytest.mark.asyncio
    async def test_plan_creation(
        self,
        mock_workflow_agent,
        mock_db,
        test_user_id,
        test_project_id,
        test_chat_history,
    ):
        """Test plan creation functionality"""
        # Create test data
        test_user = User(id=test_user_id, email="test@example.com", name="Test User")
        mock_db.add(test_user)

        test_project = Project(
            id=test_project_id,
            user_id=test_user_id,
            name="Test Project",
            description="Test Description",
            prompt="Test prompt",
            status="loading",
        )
        mock_db.add(test_project)

        # Test plan creation
        plan_text = "1. Data Collection\n2. Data Cleaning\n3. Data Processing"
        steps = mock_workflow_agent._parse_plan_into_steps(plan_text)

        assert len(steps) == 3
        assert "Data Collection" in steps[0]
        assert "Data Cleaning" in steps[1]
        assert "Data Processing" in steps[2]

    @pytest.mark.asyncio
    async def test_workflow_generation(
        self, mock_workflow_agent, mock_db, test_user_id, test_project_id
    ):
        """Test workflow generation from plan"""
        # Create test data
        test_user = User(id=test_user_id, email="test@example.com", name="Test User")
        mock_db.add(test_user)

        test_project = Project(
            id=test_project_id,
            user_id=test_user_id,
            name="Test Project",
            description="Test Description",
            prompt="Test prompt",
            status="loading",
        )
        mock_db.add(test_project)

        # Test workflow storage
        workflow_data = {
            "nodes": [{"id": "A", "name": "Test Node", "type": "task"}],
            "edges": [],
            "state_variables": ["var1", "var2"],
            "decision_points": ["decision1"],
        }

        workflow = await mock_workflow_agent._store_workflow_in_db(
            mock_db,
            test_user_id,
            test_project_id,
            workflow_data,
            "test",
            "Test plan",
            "flowchart TD\nA[Test Node]",
        )

        assert workflow is not None
        assert workflow.name == "Generated Workflow - Test"


class TestMockDatabase:
    """Test class for mock database functionality"""

    def test_mock_database_add(self, mock_db):
        """Test that mock database can add objects"""
        user = User(id=uuid.uuid4(), email="test@test.com", name="Test User")
        mock_db.add(user)

        assert len(mock_db.data["users"]) == 1
        assert mock_db.data["users"][0] == user

    def test_mock_database_commit(self, mock_db):
        """Test that mock database can commit"""
        assert not mock_db.committed
        mock_db.commit()
        assert mock_db.committed

    def test_mock_query(self, mock_db):
        """Test that mock query works correctly"""
        user = User(id=uuid.uuid4(), email="test@test.com", name="Test User")
        mock_db.add(user)

        query_result = mock_db.query(User)
        result = query_result.all()

        assert len(result) == 1
        assert result[0] == user


class TestMockAI:
    """Test class for mock AI functionality"""

    def test_mock_ai_response(self, mock_ai_response):
        """Test that mock AI response works correctly"""
        assert (
            mock_ai_response.output.plan
            == "1. Data Collection\n2. Data Cleaning\n3. Data Processing\n4. Results Analysis"
        )
        assert (
            mock_ai_response.output.summary
            == "A comprehensive data processing workflow"
        )
        assert len(mock_ai_response.output.key_phases) == 4


if __name__ == "__main__":
    # Allow running with python directly for debugging
    pytest.main([__file__, "-v"])
