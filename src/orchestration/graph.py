"""
LangGraph parent workflow that orchestrates prev stages (1-3)
"""
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy
from src.orchestration.nodes import OrchestrationNodes
from src.orchestration.routing import route_after_user_interaction
from src.orchestration.state import ParkingWorkflowState

def _retry_external_service(exc):
    """Retry transient integration failures, not validation/authorization errors."""
    return not isinstance(exc, (ValueError, KeyError, PermissionError))

def build_workflow_graph(nodes, checkpointer):
    """Build and compile the Stage 4 Graph API workflow."""
    builder = StateGraph(ParkingWorkflowState)
    builder.add_node("user_interaction", nodes.user_interaction)
    builder.add_node("submit_admin_review", nodes.submit_admin_review)
    builder.add_node("administrator_approval", nodes.administrator_approval)
    builder.add_node(
        "record_reservation",
        nodes.record_reservation,
        retry_policy=RetryPolicy(
            max_attempts=3,
            initial_interval=0.5,
            backoff_factor=2.0,
            max_interval=4.0,
            retry_on=_retry_external_service))
    builder.add_node("finalize", nodes.finalize)

    builder.add_edge(START, "user_interaction")
    builder.add_conditional_edges(
        "user_interaction",
        route_after_user_interaction,
        {
            "submit_admin_review": "submit_admin_review",
            "finalize": "finalize"})
    builder.add_edge("submit_admin_review", "administrator_approval")
    builder.add_edge("record_reservation", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)
