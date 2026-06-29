from unittest.mock import Mock
from src.orchestration.nodes import OrchestrationNodes, _normalize_mcp_result

def build_nodes():
    return OrchestrationNodes(Mock(), Mock(), Mock(), Mock())

def test_user_interaction_reuses_chatbot_and_loads_reservation():
    nodes = build_nodes()
    nodes.chatbot.process_message.return_value = {
        "response": "created",
        "reservation_id": "r-1"}
    nodes.database.get_reservation.return_value = {"id": "r-1"}

    result = nodes.user_interaction(
        {
            "workflow_id": "w-1",
            "session_id": "s-1",
            "user_message": "book"})

    assert result["reservation_id"] == "r-1"
    assert result["reservation"] == {"id": "r-1"}
    nodes.chatbot.process_message.assert_called_once_with("book", session_id="s-1")

def test_record_reservation_normalizes_mcp_text_content():
    nodes = build_nodes()
    nodes.mcp_recorder.record.return_value = [
        {"type": "text", "text": '{"status":"recorded"}'}]

    result = nodes.record_reservation({"reservation_id": "r-1"})

    assert result["recording_status"] == "recorded"
    nodes.mcp_recorder.record.assert_called_once_with("r-1")

def test_finalize_refused_reservation_does_not_claim_recording():
    result = build_nodes().finalize(
        {"reservation_id": "r-1", "admin_decision": "refused"})
    assert result["workflow_status"] == "completed"
    assert "refused" in result["final_response"]

def test_normalize_mcp_result_accepts_plain_dict():
    assert _normalize_mcp_result({"status": "already_recorded"}) == {
        "status": "already_recorded"}
