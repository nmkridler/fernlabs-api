#!/usr/bin/env python3
"""
Basic test to verify the project structure works
"""

import pytest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test that all modules can be imported"""
    try:
        from fernlabs_api.settings import APISettings
        from fernlabs_api.schema.workflow import WorkflowGenerationRequest
        from fernlabs_api.workflow.workflow_agent import WorkflowAgent
        from fernlabs_api.workflow.executor import WorkflowExecutor

        # If we get here, imports were successful
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


def test_settings():
    """Test settings configuration"""
    try:
        from fernlabs_api.settings import APISettings

        settings = APISettings()
        assert hasattr(settings, "api_host")
        assert hasattr(settings, "api_port")
        assert settings.api_host is not None
        assert settings.api_port is not None
    except Exception as e:
        pytest.fail(f"Settings test failed: {e}")


def test_schema_validation():
    """Test Pydantic schema validation"""
    try:
        from fernlabs_api.schema.workflow import WorkflowGenerationRequest

        # Test valid data
        valid_data = {
            "project_description": "Test project",
            "project_type": "data_analysis",
        }
        request = WorkflowGenerationRequest(**valid_data)
        assert request.project_description == "Test project"
        assert request.project_type == "data_analysis"
    except Exception as e:
        pytest.fail(f"Schema validation failed: {e}")


def test_project_structure():
    """Test that the project structure is correct"""
    # Check that key directories exist
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    expected_dirs = ["fernlabs_api", "tests", "alembic"]
    for dir_name in expected_dirs:
        dir_path = os.path.join(project_root, dir_name)
        assert os.path.exists(dir_path), f"Directory {dir_name} does not exist"

    # Check that key files exist
    expected_files = ["pyproject.toml", "requirements.txt", "pytest.ini"]
    for file_name in expected_files:
        file_path = os.path.join(project_root, file_name)
        assert os.path.exists(file_path), f"File {file_name} does not exist"
