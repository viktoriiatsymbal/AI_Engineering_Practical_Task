from unittest.mock import Mock
from src.orchestration.service import ParkingWorkflowService

def test_start_uses_workflow_id_as_langgraph_thread_id():
    graph = Mock()
    graph.invoke.return_value = {
        "workflow_status": "completed",
        "final_response": "done"}
    service = ParkingWorkflowService(graph)

    result = service.start("hello", session_id="s-1", workflow_id="w-1")

    assert result["workflow_id"] == "w-1"
    config = graph.invoke.call_args.kwargs["config"]
    assert config["configurable"]["thread_id"] == "w-1"


def test_resume_admin_uses_command_resume_payload():
    graph = Mock()
    graph.invoke.return_value = {
        "workflow_status": "completed",
        "admin_decision": "refused"}
    service = ParkingWorkflowService(graph)

    result = service.resume_admin("w-1", "refuse", "full")

    command = graph.invoke.call_args.args[0]
    assert command.resume == {"decision": "refuse", "comment": "full"}
    assert result["status"] == "completed"
