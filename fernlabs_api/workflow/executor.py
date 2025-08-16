"""
Workflow executor using pydantic-graph
"""

from typing import Dict, Any, Optional
import asyncio
import logging
from datetime import datetime
from pydantic_graph import Graph, BaseNode as Node, Edge
from fernlabs_api.schema.workflow import (
    WorkflowDefinition,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
)
from fernlabs_api.settings import APISettings


logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """Executes workflows using pydantic-graph"""

    def __init__(self, settings: APISettings):
        self.settings = settings

    async def execute_workflow(
        self, workflow: WorkflowDefinition, request: WorkflowExecutionRequest
    ) -> WorkflowExecutionResponse:
        """Execute a workflow with the given initial state"""

        try:
            # Create execution response
            execution_id = f"exec_{datetime.now().isoformat()}"
            execution_response = WorkflowExecutionResponse(
                execution_id=execution_id,
                workflow_id=request.workflow_id,
                status="running",
                started_at=datetime.now(),
                current_state=request.initial_state or {},
            )

            # Build the graph from workflow definition
            graph = self._build_graph(workflow)

            # Initialize state
            state = request.initial_state or {}
            state.update(self._get_default_state(workflow))

            # Execute the workflow
            final_state = await self._execute_graph(graph, state, workflow)

            # Update execution response
            execution_response.status = "completed"
            execution_response.completed_at = datetime.now()
            execution_response.results = final_state
            execution_response.current_state = final_state

            # Calculate duration
            if execution_response.started_at and execution_response.completed_at:
                duration = (
                    execution_response.completed_at - execution_response.started_at
                ).total_seconds()
                execution_response.total_duration = int(duration)

            return execution_response

        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")

            # Create error response
            execution_response = WorkflowExecutionResponse(
                execution_id=execution_id
                if "execution_id" in locals()
                else f"exec_{datetime.now().isoformat()}",
                workflow_id=request.workflow_id,
                status="failed",
                started_at=datetime.now(),
                error_message=str(e),
            )

            return execution_response

    def _build_graph(self, workflow: WorkflowDefinition) -> Graph:
        """Build a pydantic-graph Graph from workflow definition"""

        # Create nodes
        nodes = []
        for node_def in workflow.graph.nodes:
            node = Node(id=node_def.id, name=node_def.name, data=node_def.config or {})
            nodes.append(node)

        # Create edges
        edges = []
        for edge_def in workflow.graph.edges:
            edge = Edge(
                source=edge_def.source,
                target=edge_def.target,
                data=edge_def.metadata or {},
            )
            edges.append(edge)

        # Build graph
        graph = Graph(nodes=nodes, edges=edges)
        return graph

    def _get_default_state(self, workflow: WorkflowDefinition) -> Dict[str, Any]:
        """Get default values for state variables"""
        default_state = {}

        for state_var in workflow.state_schema:
            if state_var.default_value is not None:
                default_state[state_var.name] = state_var.default_value

        return default_state

    async def _execute_graph(
        self, graph: Graph, initial_state: Dict[str, Any], workflow: WorkflowDefinition
    ) -> Dict[str, Any]:
        """Execute the graph with the given state"""

        current_state = initial_state.copy()
        execution_log = []

        # Start from entry point
        current_node_id = workflow.entry_point

        while current_node_id and current_node_id not in workflow.exit_points:
            try:
                # Get current node
                node = graph.get_node(current_node_id)
                if not node:
                    raise ValueError(f"Node {current_node_id} not found in graph")

                # Execute node
                logger.info(f"Executing node: {current_node_id}")
                execution_log.append(
                    {
                        "node_id": current_node_id,
                        "timestamp": datetime.now().isoformat(),
                        "state_before": current_state.copy(),
                    }
                )

                # Check if this is a decision point
                if self._is_decision_point(current_node_id, workflow):
                    current_state = await self._execute_decision_point(
                        current_node_id, current_state, workflow
                    )
                else:
                    # Execute regular task node
                    current_state = await self._execute_task_node(
                        current_node_id, current_state, workflow
                    )

                execution_log[-1]["state_after"] = current_state.copy()

                # Find next node
                next_node_id = self._get_next_node(
                    current_node_id, current_state, graph, workflow
                )

                if next_node_id == current_node_id:
                    # Potential infinite loop
                    logger.warning(
                        f"Potential infinite loop detected at node {current_node_id}"
                    )
                    break

                current_node_id = next_node_id

            except Exception as e:
                logger.error(f"Error executing node {current_node_id}: {str(e)}")
                raise

        # Add final execution log entry
        execution_log.append(
            {
                "node_id": "completed",
                "timestamp": datetime.now().isoformat(),
                "state_before": current_state.copy(),
                "state_after": current_state.copy(),
            }
        )

        # Add execution log to state
        current_state["_execution_log"] = execution_log

        return current_state

    def _is_decision_point(self, node_id: str, workflow: WorkflowDefinition) -> bool:
        """Check if a node is a decision point"""
        return any(dp.node_id == node_id for dp in workflow.decision_points)

    async def _execute_decision_point(
        self, node_id: str, state: Dict[str, Any], workflow: WorkflowDefinition
    ) -> Dict[str, Any]:
        """Execute a decision point using LLM"""

        # Find decision point definition
        decision_point = next(
            dp for dp in workflow.decision_points if dp.node_id == node_id
        )

        # Build context from state variables
        context = {}
        for var_name in decision_point.context_variables:
            if var_name in state:
                context[var_name] = state[var_name]

        # TODO: Implement LLM decision making
        # For now, use a simple rule-based approach
        decision_result = self._make_simple_decision(decision_point, context)

        # Update state with decision result
        state[f"{node_id}_decision"] = decision_result

        return state

    def _make_simple_decision(
        self, decision_point: Any, context: Dict[str, Any]
    ) -> Any:
        """Make a simple decision based on context (placeholder for LLM)"""

        # This is a placeholder - in production, this would use an LLM
        # to make intelligent decisions based on the context

        # Simple example: if we have data, continue; otherwise, stop
        if "data" in context and context["data"]:
            return {"action": "continue", "reason": "Data available"}
        else:
            return {"action": "stop", "reason": "No data available"}

    async def _execute_task_node(
        self, node_id: str, state: Dict[str, Any], workflow: WorkflowDefinition
    ) -> Dict[str, Any]:
        """Execute a regular task node"""

        # This is a placeholder - in production, this would execute
        # the actual task logic based on the node configuration

        # For now, just add a timestamp
        state[f"{node_id}_executed_at"] = datetime.now().isoformat()

        return state

    def _get_next_node(
        self,
        current_node_id: str,
        state: Dict[str, Any],
        graph: Graph,
        workflow: WorkflowDefinition,
    ) -> Optional[str]:
        """Determine the next node to execute"""

        # Get outgoing edges from current node
        outgoing_edges = graph.get_edges_from(current_node_id)

        if not outgoing_edges:
            return None

        # For now, take the first edge (could be enhanced with conditional logic)
        next_node_id = outgoing_edges[0].target

        return next_node_id
