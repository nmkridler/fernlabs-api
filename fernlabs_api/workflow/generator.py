"""
AI-powered workflow generator using pydantic_ai
"""

from typing import List, Dict, Any
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from fernlabs_api.schema.workflow import (
    WorkflowGenerationRequest,
    WorkflowDefinition,
    WorkflowGraph,
    WorkflowNode,
    WorkflowEdge,
    StateVariable,
    DecisionPoint,
)
from fernlabs_api.settings import APISettings


class WorkflowGeneratorDependencies(BaseModel):
    """Dependencies for the workflow generator agent"""

    settings: APISettings
    request: WorkflowGenerationRequest


class WorkflowGenerator:
    """AI-powered workflow generator using pydantic_ai"""

    def __init__(self, settings: APISettings):
        self.settings = settings

        # Initialize the workflow generation agent
        self.workflow_agent = Agent(
            "openai:gpt-4o"
            if settings.openai_api_key
            else "google-gla:gemini-1.5-flash",
            deps_type=WorkflowGeneratorDependencies,
            output_type=WorkflowDefinition,
            system_prompt=(
                "You are an expert workflow designer. Create comprehensive workflows "
                "based on project descriptions, requirements, and constraints. "
                "Always return valid WorkflowDefinition objects with proper graph structure, "
                "state variables, and decision points."
            ),
        )

    async def generate_workflow(
        self, request: WorkflowGenerationRequest
    ) -> WorkflowDefinition:
        """Generate a complete workflow definition from user description"""

        # Create the generation prompt
        prompt = self._create_generation_prompt(request)

        # Create dependencies for the agent
        deps = WorkflowGeneratorDependencies(settings=self.settings, request=request)

        # Use pydantic_ai agent to generate the workflow
        result = await self.workflow_agent.run(prompt, deps=deps)
        return result.output

    def _create_generation_prompt(self, request: WorkflowGenerationRequest) -> str:
        """Create a detailed prompt for workflow generation"""

        prompt = f"""
        Create a comprehensive workflow for the following project:

        Project Description: {request.project_description}
        Project Type: {request.project_type or "general"}

        {f"Requirements: {', '.join(request.requirements)}" if request.requirements else ""}
        {f"Constraints: {', '.join(request.constraints)}" if request.constraints else ""}

        Please design a workflow that includes:

        1. A clear graph structure with nodes representing tasks, decisions, and control flow
        2. State variables that track the progress and data throughout the workflow
        3. Decision points where an LLM can make intelligent choices about the next steps
        4. Proper entry and exit points
        5. Logical transitions between nodes

        The workflow should be:
        - Self-contained and executable
        - Well-structured for automation
        - Flexible enough to handle variations in data and conditions
        - Clear about what each node does and when decisions are made

        Return a complete WorkflowDefinition with all required components.
        """

        return prompt

    async def generate_python_code(self, workflow: WorkflowDefinition) -> str:
        """Generate executable Python code for the workflow"""

        # Create a code generation agent
        code_agent = Agent(
            "openai:gpt-4o"
            if self.settings.openai_api_key
            else "google-gla:gemini-1.5-flash",
            output_type=str,
            system_prompt=(
                "You are an expert Python developer. Generate clean, executable Python code "
                "for workflow definitions. Always return only the Python code with no explanations."
            ),
        )

        code_prompt = f"""
        Generate executable Python code for the following workflow definition:

        {workflow.model_dump_json(indent=2)}

        The code should:
        1. Use pydantic-graph for graph execution
        2. Include proper error handling
        3. Have clear state management
        4. Include unit tests
        5. Be well-documented
        6. Follow Python best practices

        Return only the Python code, no explanations.
        """

        # Use pydantic_ai to generate the code
        result = await code_agent.run(code_prompt)
        return result.output

    async def generate_unit_tests(self, workflow: WorkflowDefinition, code: str) -> str:
        """Generate unit tests for the workflow code"""

        # Create a test generation agent
        test_agent = Agent(
            "openai:gpt-4o"
            if self.settings.openai_api_key
            else "google-gla:gemini-1.5-flash",
            output_type=str,
            system_prompt=(
                "You are an expert Python tester. Generate comprehensive unit tests "
                "for workflow code. Always return only the Python test code with no explanations."
            ),
        )

        test_prompt = f"""
        Generate comprehensive unit tests for the following workflow code:

        Code:
        {code}

        Workflow Definition:
        {workflow.model_dump_json(indent=2)}

        The tests should:
        1. Test each node in the workflow
        2. Test state transitions
        3. Test decision points
        4. Test error conditions
        5. Use pytest
        6. Include proper mocking where needed
        7. Test edge cases

        Return only the Python test code, no explanations.
        """

        # Use pydantic_ai to generate the tests
        result = await test_agent.run(test_prompt)
        return result.output

    async def validate_workflow(self, workflow: WorkflowDefinition) -> Dict[str, Any]:
        """Validate the generated workflow for correctness and completeness"""

        # Create a validation agent
        validation_agent = Agent(
            "openai:gpt-4o"
            if self.settings.openai_api_key
            else "google-gla:gemini-1.5-flash",
            output_type=Dict[str, Any],
            system_prompt=(
                "You are an expert workflow validator. Analyze workflow definitions "
                "for correctness, completeness, and potential issues. Return structured validation reports."
            ),
        )

        validation_prompt = f"""
        Validate the following workflow definition for correctness and completeness:

        {workflow.model_dump_json(indent=2)}

        Check for:
        1. Graph connectivity (all nodes reachable)
        2. State variable consistency
        3. Decision point logic
        4. Entry/exit point validity
        5. Potential infinite loops
        6. Missing dependencies

        Return a validation report with:
        - Overall validity (true/false)
        - Issues found (list)
        - Recommendations (list)
        - Severity levels for issues
        """

        # Use pydantic_ai to validate the workflow
        result = await validation_agent.run(validation_prompt)
        return result.output
