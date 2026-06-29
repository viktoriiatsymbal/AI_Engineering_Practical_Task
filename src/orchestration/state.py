"""
Shared state for the parent LangGraph
"""
from typing import Any, Literal
from typing_extensions import NotRequired, TypedDict

class ParkingWorkflowState(TypedDict):
    """State persisted by LangGraph between chatbot, HITL and MCP nodes."""

    workflow_id: str
    session_id: str
    user_message: str

    assistant_response: NotRequired[str]
    reservation_id: NotRequired[str]
    reservation: NotRequired[dict[str, Any]]

    admin_thread_id: NotRequired[str]
    admin_decision: NotRequired[Literal["approved", "refused"]]
    admin_comment: NotRequired[str | None]

    recording_status: NotRequired[
        Literal["not_started", "pending", "recorded", "already_recorded", "failed"]]
    recording_result: NotRequired[Any]

    workflow_status: NotRequired[
        Literal[
            "responded",
            "waiting_for_admin",
            "approved",
            "refused",
            "completed",
            "failed"]]
    final_response: NotRequired[str]
    error: NotRequired[str | None]
