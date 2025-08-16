#!/usr/bin/env python3
"""
Basic test to verify the project structure works
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test that all modules can be imported"""
    try:
        from fernlabs_api.settings import APISettings
        from fernlabs_api.schema.workflow import WorkflowGenerationRequest
        from fernlabs_api.workflow.generator import WorkflowGenerator
        from fernlabs_api.workflow.executor import WorkflowExecutor

        print("✅ All imports successful!")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_settings():
    """Test settings configuration"""
    try:
        from fernlabs_api.settings import APISettings

        settings = APISettings()
        print(
            f"✅ Settings loaded: API_HOST={settings.api_host}, API_PORT={settings.api_port}"
        )
        return True
    except Exception as e:
        print(f"❌ Settings test failed: {e}")
        return False


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
        print(f"✅ Schema validation successful: {request.project_description}")
        return True
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Running basic tests...")
    print()

    tests = [test_imports, test_settings, test_schema_validation]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Project structure is working correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)
