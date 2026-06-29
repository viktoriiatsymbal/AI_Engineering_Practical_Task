from unittest.mock import Mock
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from src.orchestration.graph import build_workflow_graph
from src.orchestration.nodes import OrchestrationNodes

def make_graph(*, reservation=False):
    chatbot = Mock()
    database = Mock()
    admin_agent = Mock()
    recorder = Mock()

    response = {"response": "info answer"}
    if reservation:
        response["reservation_id"] = "r-1"
        database.get_reservation.return_value = {
            "id": "r-1",
            "name": "Anna",
            "surname": "Smith",
            "status": "pending"}
        database.get_admin_review.side_effect = [
            None,
            {
                "thread_id": "admin-w-1",
                "review_state": "approved"}]
        database.create_admin_review.return_value = {
            "thread_id": "admin-w-1"}
        admin_agent.propose.return_value = {
            "action_requests": [{"name": "approve_reservation"}]}
        recorder.record.return_value = {"status": "recorded"}
    chatbot.process_message.return_value = response

    graph = build_workflow_graph(
        OrchestrationNodes(chatbot, database, admin_agent, recorder),
        InMemorySaver())
    return graph, chatbot, database, admin_agent, recorder

def test_information_path_finishes_without_admin_or_mcp():
    graph, _, database, admin_agent, recorder = make_graph(reservation=False)
    result = graph.invoke(
        {
            "workflow_id": "w-info",
            "session_id": "s-info",
            "user_message": "Where is the parking?"},
        {"configurable": {"thread_id": "w-info"}})

    assert result["workflow_status"] == "completed"
    assert result["final_response"] == "info answer"
    database.create_admin_review.assert_not_called()
    admin_agent.propose.assert_not_called()
    recorder.record.assert_not_called()

def test_approved_path_interrupts_then_records_through_mcp():
    graph, _, _, admin_agent, recorder = make_graph(reservation=True)
    config = {"configurable": {"thread_id": "w-1"}}

    first = graph.invoke(
        {
            "workflow_id": "w-1",
            "session_id": "s-1",
            "user_message": "book"},
        config)
    assert first["__interrupt__"]

    result = graph.invoke(
        Command(resume={"decision": "approve", "comment": "ok"}),
        config)

    assert result["workflow_status"] == "completed"
    assert result["admin_decision"] == "approved"
    assert result["recording_status"] == "recorded"
    admin_agent.resume.assert_called_once_with(
        thread_id="admin-w-1", decision="approve", message="ok")
    recorder.record.assert_called_once_with("r-1")
