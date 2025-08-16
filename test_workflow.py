#!/usr/bin/env python3
"""
Test script for the new workflow system using FastAPI background tasks
"""

import requests
import json
import time
import uuid

# API base URL
BASE_URL = "http://localhost:8000/api/v1"


def test_create_project():
    """Test creating a new project with workflow generation"""

    # Test project data
    project_data = {
        "name": "Test Data Analysis Project",
        "description": "A test project to verify workflow generation",
        "project_type": "data_analysis",
        "github_repo": "https://github.com/testuser/testrepo",
        "prompt": "Create a workflow that reads CSV data, performs data cleaning, applies a machine learning model, and generates a report with visualizations",
    }

    print("Creating project...")
    print(f"Request data: {json.dumps(project_data, indent=2)}")

    try:
        # Create project
        response = requests.post(f"{BASE_URL}/projects/", json=project_data)

        if response.status_code == 200:
            project = response.json()
            print(f"✅ Project created successfully!")
            print(f"Project ID: {project['id']}")
            print(f"Status: {project['status']}")
            print(f"Response: {json.dumps(project, indent=2)}")

            # Store project ID for status checking
            return project["id"]
        else:
            print(f"❌ Failed to create project: {response.status_code}")
            print(f"Error: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None


def check_project_status(project_id):
    """Check the status of a project"""

    try:
        response = requests.get(f"{BASE_URL}/projects/{project_id}")

        if response.status_code == 200:
            project = response.json()
            return project["status"]
        else:
            print(f"❌ Failed to get project status: {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None


def monitor_project(project_id, max_wait_time=300):
    """Monitor project status until completion or timeout"""

    print(f"\nMonitoring project {project_id}...")
    print("Status updates:")
    print(
        "Note: FastAPI background tasks run in the same process, so they may complete quickly!"
    )

    start_time = time.time()
    last_status = None

    while time.time() - start_time < max_wait_time:
        current_status = check_project_status(project_id)

        if current_status != last_status:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] Status: {current_status}")
            last_status = current_status

            if current_status == "completed":
                print("✅ Workflow generation completed!")
                return True
            elif current_status == "failed":
                print("❌ Workflow generation failed!")
                return False

        time.sleep(2)  # Check every 2 seconds for faster response

    print("⏰ Timeout reached while monitoring project")
    return False


def test_list_projects():
    """Test listing all projects"""

    print("\nTesting project listing...")

    try:
        response = requests.get(f"{BASE_URL}/projects/")

        if response.status_code == 200:
            projects = response.json()
            print(f"✅ Found {len(projects)} projects:")
            for project in projects:
                print(
                    f"  - {project['name']} (ID: {project['id']}, Status: {project['status']})"
                )
        else:
            print(f"❌ Failed to list projects: {response.status_code}")
            print(f"Error: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")


def main():
    """Main test function"""

    print("🚀 Testing FernLabs API Workflow System (FastAPI Background Tasks)")
    print("=" * 70)

    # Test 1: Create project
    project_id = test_create_project()

    if not project_id:
        print("❌ Cannot proceed without a valid project ID")
        return

    # Test 2: Monitor project status
    success = monitor_project(project_id)

    # Test 3: List all projects
    test_list_projects()

    # Test 4: Get final project details
    if success:
        print(f"\n🎉 Final project details:")
        final_status = check_project_status(project_id)
        print(f"Project ID: {project_id}")
        print(f"Final Status: {final_status}")

    print("\n" + "=" * 70)
    print("🏁 Test completed!")
    print("\n💡 Note: FastAPI background tasks run in-process, so workflow generation")
    print("   may complete very quickly depending on the AI model response time.")


if __name__ == "__main__":
    main()
