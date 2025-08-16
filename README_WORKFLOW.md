# FernLabs API Workflow System

This document describes the new workflow system for the FernLabs API.

## Overview

The new workflow system implements an asynchronous, AI-powered workflow generation process:

1. **User Request**: User submits a project creation request with a prompt
2. **Project Creation**: A new project is created in the database with "loading" status
3. **Background Task**: A FastAPI background task is launched to process the workflow generation
4. **Immediate Response**: The API immediately returns the project ID
5. **AI Processing**: The planning agent processes the prompt and generates a workflow
6. **Completion**: The project status is updated to "completed" with the generated workflow

## API Endpoints

### Create Project
```
POST /api/v1/projects/
```

**Request Body:**
```json
{
  "name": "My Data Analysis Project",
  "description": "Analyze customer data and generate insights",
  "project_type": "data_analysis",
  "github_repo": "https://github.com/user/repo",
  "prompt": "Create a workflow that processes CSV data, applies machine learning models, and generates visualizations"
}
```

**Response:**
```json
{
  "id": "uuid-here",
  "user_id": "user-uuid-here",
  "name": "My Data Analysis Project",
  "description": "Analyze customer data and generate insights",
  "project_type": "data_analysis",
  "github_repo": "https://github.com/user/repo",
  "prompt": "Create a workflow that processes CSV data, applies machine learning models, and generates visualizations",
  "status": "loading",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Check Project Status
```
GET /api/v1/projects/{project_id}
```

The status will be one of:
- `loading`: Workflow generation in progress
- `completed`: Workflow generated successfully
- `failed`: Workflow generation failed

## Background Tasks

The system uses FastAPI's built-in BackgroundTasks for asynchronous processing:

### Workflow Generation Task
- **Task Name**: `generate_workflow_background`
- **Purpose**: Processes user prompts and generates AI workflows
- **Input**: Project ID and User ID
- **Output**: Generated workflow stored in database

### Code Generation Task
- **Task Name**: `generate_workflow_code_background`
- **Purpose**: Generates executable Python code from workflows
- **Input**: Workflow ID
- **Output**: Python code and unit tests

## Running the System

### 1. Start the API Server
```bash
cd fernlabs-api
uvicorn fernlabs_api.app:app --reload
```

### 2. Run Database Migration (if needed)
```bash
cd fernlabs-api
python migrate_db.py
```

## Database Schema Changes

### Projects Table
- Added `prompt` field (TEXT, NOT NULL) for user workflow requests
- Updated `status` field default to "loading"
- Status values: "loading", "completed", "failed", "active", "archived", "deleted"

### Workflows Table
- Stores generated workflow definitions
- Includes graph structure, state schema, and decision points
- Links to projects via `project_id`

## Error Handling

- Database errors are caught and return appropriate HTTP status codes
- Background task failures update project status to "failed"
- Rollback mechanisms ensure database consistency

## Advantages of FastAPI Background Tasks

- **Simplified Setup**: No need for Redis or Celery
- **Built-in**: Part of FastAPI framework, no additional dependencies
- **Async Support**: Native async/await support
- **Easy Debugging**: Tasks run in the same process for easier debugging
- **Lightweight**: Perfect for moderate background processing needs

## Future Enhancements

- Authentication and user management
- Real-time status updates via WebSockets
- Workflow execution engine
- Artifact storage and management
- Workflow versioning and history
- For high-volume processing, consider migrating to Celery or similar task queue
