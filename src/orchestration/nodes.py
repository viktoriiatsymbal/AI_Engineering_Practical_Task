"""
Nodes that reuse the stage 1-3 components
"""
import json
from dataclasses import dataclass
from typing import Any
from langgraph.types import Command, interrupt

@dataclass
class OrchestrationNodes:
    """Dependency-injected node collection for the parent graph."""

    chatbot: Any
    database: Any
    admin_agent: Any
    mcp_recorder: Any

    def user_interaction(self, state):
        result = self.chatbot.process_message(
            state["user_message"],
            session_id=state["session_id"])
        update = {
            "assistant_response": result["response"],
            "workflow_status": "responded",
            "recording_status": "not_started",
            "error": None}
        reservation_id = result.get("reservation_id")
        if reservation_id:
            update["reservation_id"] = reservation_id
            reservation = self.database.get_reservation(reservation_id)
            if reservation is None:
                raise RuntimeError(
                    f"Reservation was created but cannot be loaded: {reservation_id}")
            update["reservation"] = reservation
        return update

    def submit_admin_review(self, state):
        reservation_id = state["reservation_id"]
        existing = self.database.get_admin_review(reservation_id)
        if existing is None:
            review = self.database.create_admin_review(
                reservation_id=reservation_id,
                thread_id=f"admin-{state['workflow_id']}")
        else:
            review = existing

        return {
            "admin_thread_id": review["thread_id"],
            "workflow_status": "waiting_for_admin"}

    def administrator_approval(self, state):
        """Pause the parent graph, then execute the existing Stage 2 agent."""
        decision = interrupt(
            {
                "type": "reservation_approval",
                "workflow_id": state["workflow_id"],
                "reservation_id": state["reservation_id"],
                "reservation": state["reservation"],
                "question": "Approve or refuse this parking reservation?",
                "allowed_decisions": ["approve", "refuse"]})
        if not isinstance(decision, dict):
            raise ValueError("Administrator decision must be a JSON object")

        action = str(decision.get("decision", "")).strip().lower()
        if action not in {"approve", "refuse"}:
            raise ValueError("Decision must be 'approve' or 'refuse'")

        comment = decision.get("comment")
        reservation_id = state["reservation_id"]
        admin_thread_id = state["admin_thread_id"]
        instruction = (
            "approve this reservation"
            if action == "approve"
            else "refuse this reservation")

        proposal = self.admin_agent.propose(
            reservation_id=reservation_id,
            instruction=instruction,
            thread_id=admin_thread_id)
        expected_tool = (
            "approve_reservation"
            if action == "approve"
            else "refuse_reservation")
        proposed_tools = {
            item.get("name") for item in proposal.get("action_requests", [])}
        if expected_tool not in proposed_tools:
            raise RuntimeError(
                f"Administrator agent proposed {proposed_tools}, expected {expected_tool}")

        self.admin_agent.resume(
            thread_id=admin_thread_id,
            decision="approve",
            message=str(comment) if comment else None)

        review = self.database.get_admin_review(reservation_id)
        if review is None:
            raise RuntimeError("Administrator review disappeared after execution")
        resolved = review["review_state"]
        if resolved not in {"approved", "refused"}:
            raise RuntimeError(f"Unexpected resolved review state: {resolved}")

        return Command(
            update={
                "admin_decision": resolved,
                "admin_comment": comment,
                "workflow_status": resolved},
            goto=("record_reservation" if resolved == "approved" else "finalize"))

    def record_reservation(self, state):
        """Call the real Stage 3 MCP tool through the LangChain MCP adapter."""
        result = self.mcp_recorder.record(state["reservation_id"])
        normalized = _normalize_mcp_result(result)
        status = normalized.get("status", "recorded")
        if status not in {"recorded", "already_recorded"}:
            raise RuntimeError(f"Unexpected MCP recording status: {status}")
        return {
            "recording_status": status,
            "recording_result": normalized}

    def finalize(self, state):
        decision = state.get("admin_decision")
        if decision == "approved":
            recording_status = state.get("recording_status", "recorded")
            message = (
                f"Reservation {state['reservation_id']} was approved and "
                f"stored by the MCP server ({recording_status}).")
        elif decision == "refused":
            message = f"Reservation {state['reservation_id']} was refused."
        else:
            message = state.get("assistant_response", "Workflow completed.")

        return {
            "workflow_status": "completed",
            "final_response": message,
            "error": None}

def _normalize_mcp_result(result):
    """Normalize LangChain/FastMCP result variants into a plain dictionary."""
    if isinstance(result, dict):
        return result

    content = getattr(result, "content", result)
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else {"result": parsed}
        except json.JSONDecodeError:
            return {"status": "recorded", "result": content}

    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                try:
                    parsed = json.loads(item["text"])
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue

    return {"status": "recorded", "result": str(content)}
