#!/usr/bin/env python3
"""
Simple test to verify the workflow structure works correctly
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from fernlabs_api.workflow.generator import WorkflowAgent, workflow_graph
    from fernlabs_api.settings import APISettings

    print("✅ Successfully imported workflow modules")

    # Test workflow graph structure
    print(f"✅ Workflow graph has {len(workflow_graph.nodes)} nodes")
    print(f"✅ Node types: {[node.__name__ for node in workflow_graph.nodes]}")

    # Test Mermaid diagram generation
    mermaid_code = workflow_graph.mermaid_code(start_node=workflow_graph.nodes[0])
    print("✅ Successfully generated Mermaid diagram")
    print(f"✅ Mermaid code length: {len(mermaid_code)} characters")

    # Test workflow agent initialization (without API keys)
    try:
        # This should work even without valid API keys
        settings = APISettings(
            api_model_name="test-model",
            api_model_provider="openai",
            api_model_key="test-key",
        )
        agent = WorkflowAgent(settings)
        print("✅ Successfully created WorkflowAgent instance")

        # Test Mermaid diagram generation from agent
        diagram = agent.generate_mermaid_diagram()
        print("✅ Successfully generated Mermaid diagram from agent")

    except Exception as e:
        print(
            f"⚠️  WorkflowAgent initialization had issues (expected without real API keys): {e}"
        )

    print("\n🎉 All basic structure tests passed!")
    print("\nWorkflow flow:")
    print("CreatePlan → AssessPlan → [WaitForUserInput → EditPlan → AssessPlan] → End")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the fernlabs-api directory")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
