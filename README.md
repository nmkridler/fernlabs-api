# FernLabs API

AI-powered workflow generation tool for developers. This API allows users to describe projects and automatically generates AI-powered workflows that can be executed, tested, and deployed.

## Features

- **AI Workflow Generation**: Describe your project and get a complete workflow automatically generated
- **Workflow Execution**: Run workflows with data and track execution progress
- **Project Management**: Organize workflows into projects with version control
- **Artifact Management**: Upload and manage data files, models, and other artifacts
- **Execution Tracking**: Monitor workflow executions with detailed logs and results
- **Code Generation**: Automatically generate executable Python code and unit tests
- **Graph Visualization**: View workflows as state machine graphs

## Architecture

The project uses:
- **FastAPI** for the REST API
- **pydantic-ai** for AI-powered workflow generation
- **pydantic-graph** for workflow execution and graph management
- **SQLAlchemy** for database operations
- **PostgreSQL** as the primary database
- **Redis** for caching and task queues
- **Alembic** for database migrations

## Project Structure

```
fernlabs-api/
├── alembic/                 # Database migrations
├── fernlabs_api/           # Main application code
│   ├── db/                 # Database models
│   ├── routes/             # API route handlers
│   ├── schema/             # Pydantic schemas
│   ├── workflow/           # Workflow generation and execution
│   ├── app.py              # FastAPI application
│   └── settings.py         # Configuration
├── docker-compose.yaml     # Docker services
├── Dockerfile              # Container definition
├── Makefile                # Development commands
├── pyproject.toml          # Project configuration
└── requirements.txt        # Python dependencies
```

## Quick Start

### Prerequisites

- Python 3.10+
- Docker and Docker Compose
- OpenAI API key (for AI workflow generation)

### Development Setup

1. **Clone and setup the project**:
   ```bash
   cd fernlabs-api
   make setup
   ```

2. **Start the services**:
   ```bash
   make docker-run
   ```

3. **Run migrations**:
   ```bash
   make db-migrate
   ```

4. **Start development server**:
   ```bash
   make dev
   ```

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://postgres:password@localhost/fernlabs

# Redis
REDIS_URL=redis://localhost:6379

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
```

## API Endpoints

### Workflows

- `POST /api/v1/workflows/generate` - Generate a new AI workflow
- `POST /api/v1/workflows/{id}/execute` - Execute a workflow
- `GET /api/v1/workflows/{id}` - Get workflow details
- `GET /api/v1/workflows/{id}/code` - Get generated Python code
- `GET /api/v1/workflows/{id}/tests` - Get unit tests

### Projects

- `POST /api/v1/projects/` - Create a new project
- `GET /api/v1/projects/` - List user projects
- `GET /api/v1/projects/{id}` - Get project details
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Executions

- `GET /api/v1/executions/` - List workflow executions
- `GET /api/v1/executions/{id}` - Get execution details
- `GET /api/v1/executions/workflow/{id}` - Get executions for a workflow

### Artifacts

- `POST /api/v1/artifacts/upload` - Upload a new artifact
- `GET /api/v1/artifacts/` - List artifacts
- `GET /api/v1/artifacts/{id}` - Get artifact details
- `GET /api/v1/artifacts/{id}/download` - Download artifact

## Usage Examples

### Generate a Workflow

```python
import requests

# Generate a data analysis workflow
response = requests.post("http://localhost:8000/api/v1/workflows/generate", json={
    "project_description": "Analyze customer data to identify purchasing patterns",
    "project_type": "data_analysis",
    "requirements": [
        "Load CSV data",
        "Clean and preprocess data",
        "Perform statistical analysis",
        "Generate visualizations",
        "Create summary report"
    ]
})

workflow = response.json()
print(f"Generated workflow: {workflow['name']}")
```

### Execute a Workflow

```python
# Execute the generated workflow
execution_response = requests.post(
    f"http://localhost:8000/api/v1/workflows/{workflow['id']}/execute",
    json={
        "workflow_id": workflow['id'],
        "initial_state": {
            "data_file": "customers.csv",
            "analysis_type": "purchasing_patterns"
        }
    }
)

execution = execution_response.json()
print(f"Execution status: {execution['status']}")
```

## Development

### Available Commands

```bash
make help              # Show all available commands
make install           # Install dependencies
make dev              # Start development server
make test             # Run tests
make db-migrate       # Run database migrations
make db-revision      # Create new migration
make docker-build     # Build Docker image
make docker-run       # Start services with Docker Compose
make docker-stop      # Stop Docker services
```

### Adding New Features

1. **Database Models**: Add new models in `fernlabs_api/db/model.py`
2. **Schemas**: Create Pydantic schemas in `fernlabs_api/schema/`
3. **Routes**: Add API endpoints in `fernlabs_api/routes/`
4. **Migrations**: Generate and run migrations with `make db-revision`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For questions and support, please open an issue on GitHub or contact the development team.
