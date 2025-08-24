# Testing the WorkflowAgent Generator with pytest

This directory contains pytest-based test modules to verify the functionality of the `WorkflowAgent` class in `fernlabs_api/workflow/generator.py`.

## Test Structure

```
fernlabs-api/
├── tests/
│   ├── __init__.py                    # Makes tests a Python package
│   ├── conftest.py                    # Shared pytest fixtures and configuration
│   ├── test_generator_simple.py       # Basic functionality tests
│   ├── test_generator.py              # Comprehensive test suite
│   └── README_TESTING.md              # This file
├── pytest.ini                         # Pytest configuration
├── run_tests.py                       # Test runner script
└── fernlabs_api/
    └── workflow/
        └── generator.py               # Code being tested
```

## Test Modules

### 1. `test_generator_simple.py` - Basic Functionality Tests

A pytest module that tests core functionality without complex mocking or AI integration.

**Features:**
- Import validation
- Model creation tests
- Plan parsing functionality
- Mermaid chart generation
- Error handling
- Settings validation

**Usage:**
```bash
# From the project root
cd fernlabs-api
python -m pytest tests/test_generator_simple.py -v

# Or use the test runner
python run_tests.py --basic
```

**What it tests:**
- ✅ Basic imports and dependencies
- ✅ Pydantic model creation
- ✅ Plan parsing logic
- ✅ Mermaid chart generation
- ✅ Error handling for invalid data
- ✅ Settings configuration

### 2. `test_generator.py` - Comprehensive Test Suite

A full-featured pytest module with mocking capabilities for testing AI integration.

**Features:**
- Mock database sessions
- Mock AI responses
- Full workflow testing
- Database operation testing
- Agent call logging
- Async functionality testing

**Usage:**
```bash
# From the project root
cd fernlabs-api
python -m pytest tests/test_generator.py -v

# Or use the test runner
python run_tests.py --comprehensive
```

**What it tests:**
- ✅ Agent initialization and tool registration
- ✅ Plan creation and editing workflows
- ✅ Workflow generation from plans
- ✅ Mermaid chart generation
- ✅ Database operations (create, read, update)
- ✅ Error handling and logging
- ✅ Utility methods and summaries

### 3. `conftest.py` - Shared Fixtures

Provides common pytest fixtures and configuration used across all test modules.

**Features:**
- Mock database session fixtures
- Mock AI response fixtures
- Test data fixtures (user IDs, project IDs, chat history)
- Pytest configuration and markers

### 4. `pytest.ini` - Pytest Configuration

Configuration file that sets up the testing environment.

**Features:**
- Test discovery patterns
- Custom markers (unit, integration, slow, asyncio)
- Output formatting
- Import mode configuration

### 5. `run_tests.py` - Test Runner Script

A convenient script to run tests from the project root directory.

**Usage:**
```bash
cd fernlabs-api

# Run all tests (recommended)
python run_tests.py

# Run only basic tests
python run_tests.py --basic

# Run only comprehensive tests
python run_tests.py --comprehensive

# Run with coverage reporting
python run_tests.py --coverage

# Run a specific test
python run_tests.py --test "test_mermaid_generation"
```

## Prerequisites

### For Basic Tests
- Python 3.8+
- pytest
- Basic dependencies installed

### For Comprehensive Tests
- Python 3.8+
- pytest
- pytest-asyncio (for async tests)
- All project dependencies installed

### Installation
```bash
# Install pytest and related packages
pip install pytest pytest-asyncio pytest-cov

# Or install from requirements
pip install -r requirements.txt
```

## Running the Tests

### Quick Start (Recommended)
```bash
cd fernlabs-api

# Use the test runner (easiest)
python run_tests.py

# Or run with pytest directly
python -m pytest tests/ -v
```

### Advanced pytest Usage

```bash
# Run specific test file
python -m pytest tests/test_generator_simple.py -v

# Run tests matching a pattern
python -m pytest tests/ -k "mermaid" -v

# Run tests with specific markers
python -m pytest tests/ -m unit -v
python -m pytest tests/ -m asyncio -v

# Run tests with coverage
python -m pytest tests/ --cov=fernlabs_api --cov-report=html

# Run tests in parallel (requires pytest-xdist)
python -m pytest tests/ -n auto

# Run tests with detailed output
python -m pytest tests/ -v -s --tb=long
```

### Test Output Examples

**Successful pytest run:**
```
============================= test session starts ==============================
platform darwin -- Python 3.9.7, pytest-6.2.5, py-1.10.0, pluggy-0.13.1
rootdir: /path/to/fernlabs-api
plugins: asyncio-0.15.1, cov-3.0.0
collected 25 items

tests/test_generator_simple.py::test_imports PASSED                    [  4%]
tests/test_generator_simple.py::test_settings_validation PASSED       [  8%]
tests/test_generator_simple.py::test_plan_dependencies_creation PASSED [ 12%]
tests/test_generator_simple.py::test_plan_response_model PASSED       [ 16%]
tests/test_generator_simple.py::test_plan_parsing PASSED              [ 20%]
tests/test_generator_simple.py::test_mermaid_generation PASSED        [ 24%]
tests/test_generator_simple.py::test_mermaid_generation_with_decision_nodes PASSED [ 28%]
tests/test_generator_simple.py::test_error_handling PASSED            [ 32%]
tests/test_generator_simple.py::test_error_handling_empty_nodes PASSED [ 36%]
tests/test_generator_simple.py::test_plan_parsing_edge_cases PASSED   [ 40%]
tests/test_generator_simple.py::test_workflow_agent_initialization PASSED [ 44%]
tests/test_generator.py::TestWorkflowAgent::test_agent_initialization PASSED [ 48%]
tests/test_generator.py::TestWorkflowAgent::test_plan_dependencies_creation PASSED [ 52%]
tests/test_generator.py::TestWorkflowAgent::test_plan_response_model PASSED [ 56%]
tests/test_generator.py::TestWorkflowAgent::test_plan_parsing PASSED  [ 60%]
tests/test_generator.py::TestWorkflowAgent::test_mermaid_generation PASSED [ 64%]
tests/test_generator.py::TestWorkflowAgent::test_error_handling PASSED [ 68%]
tests/test_generator.py::TestWorkflowAgent::test_database_operations PASSED [ 72%]
tests/test_generator.py::TestWorkflowAgent::test_utility_methods PASSED [ 76%]
tests/test_generator.py::TestWorkflowAgentAsync::test_plan_creation PASSED [ 80%]
tests/test_generator.py::TestWorkflowAgentAsync::test_workflow_generation PASSED [ 84%]
tests/test_generator.py::TestMockDatabase::test_mock_database_add PASSED [ 88%]
tests/test_generator.py::TestMockDatabase::test_mock_database_commit PASSED [ 92%]
tests/test_generator.py::TestMockDatabase::test_mock_query PASSED     [ 96%]
tests/test_generator.py::TestMockAI::test_mock_ai_response PASSED     [100%]

============================== 25 passed in 3.45s ==============================
```

## Pytest Features Used

### Fixtures
- **Session-scoped fixtures**: `test_user_id`, `test_project_id` (created once per test session)
- **Function-scoped fixtures**: `mock_db`, `mock_workflow_agent`, `test_chat_history`
- **Shared fixtures**: Defined in `conftest.py` for use across all test modules

### Markers
- **`@pytest.mark.unit`**: Unit tests (fast, no external dependencies)
- **`@pytest.mark.integration`**: Integration tests (slower, may have external dependencies)
- **`@pytest.mark.slow`**: Slow tests that should be run separately
- **`@pytest.mark.asyncio`**: Async tests that require asyncio support

### Test Classes
- **`TestWorkflowAgent`**: Tests for basic WorkflowAgent functionality
- **`TestWorkflowAgentAsync`**: Tests for async WorkflowAgent functionality
- **`TestMockDatabase`**: Tests for mock database functionality
- **`TestMockAI`**: Tests for mock AI functionality

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure you're running from the `fernlabs-api` directory
   - Check that all dependencies are installed
   - Verify Python path includes the project root

2. **pytest Not Found**
   - Install pytest: `pip install pytest`
   - For async tests: `pip install pytest-asyncio`
   - For coverage: `pip install pytest-cov`

3. **Async Test Failures**
   - Ensure `pytest-asyncio` is installed
   - Check that async tests are properly marked with `@pytest.mark.asyncio`

### Debug Mode

For detailed debugging, run with verbose output:
```bash
# Using pytest directly
python -m pytest tests/ -v -s --tb=long

# Using the test runner
python run_tests.py --verbose
```

## Extending the Tests

### Adding New Test Cases

1. **Create new test functions** in existing test modules
2. **Use existing fixtures** from `conftest.py`
3. **Add appropriate markers** for test categorization
4. **Follow pytest naming conventions**: `test_function_name`

### Adding New Test Modules

1. **Create new file** following the pattern `test_*.py`
2. **Import shared fixtures** from `conftest.py`
3. **Add to appropriate test classes** or create new ones
4. **Update this README** with new test information

### Testing New Features

When adding new functionality to the `WorkflowAgent`:

1. Add corresponding test functions
2. Test both success and failure scenarios
3. Include edge cases and error conditions
4. Use appropriate fixtures and mocking
5. Add tests to the appropriate test class

## Integration with CI/CD

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Run Tests
  run: |
    cd fernlabs-api
    python -m pytest tests/ -v

# Or use the test runner
- name: Run Tests with Runner
  run: |
    cd fernlabs-api
    python run_tests.py

# Run with coverage
- name: Run Tests with Coverage
  run: |
    cd fernlabs-api
    python -m pytest tests/ --cov=fernlabs_api --cov-report=xml
```

## Performance Considerations

- **Unit tests**: Run in ~1-2 seconds
- **Integration tests**: Run in ~2-5 seconds
- **Full test suite**: Run in ~3-8 seconds

## Benefits of pytest

- **Modern testing framework**: Industry standard with extensive plugin ecosystem
- **Fixture system**: Efficient test setup and teardown
- **Parameterization**: Easy testing of multiple scenarios
- **Markers**: Flexible test categorization and selection
- **Plugin support**: Coverage, parallel execution, and more
- **Better error reporting**: Clear, detailed test failure information
- **IDE integration**: Excellent support in VS Code, PyCharm, etc.

## File Organization

The tests are organized in a dedicated `tests/` folder for better project structure:

- **`tests/`**: Contains all test-related files
- **`conftest.py`**: Shared fixtures and configuration
- **`pytest.ini`**: Pytest configuration
- **`run_tests.py`**: Convenient test runner from project root
- **`tests/README_TESTING.md`**: This documentation file

This organization makes it easy to:
- Run tests from anywhere in the project
- Keep test files separate from source code
- Maintain clean project structure
- Integrate with CI/CD systems
- Use pytest's powerful features effectively
