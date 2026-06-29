from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from src.admin_agent import AdminApprovalAgent

def _settings():
    return SimpleNamespace(
        llm_model="gpt-4o-mini",
        openai_api_key="test-key",
        postgres_checkpoint_dsn="postgresql://unused")

def test_agent_uses_real_human_in_the_loop_middleware():
    database = MagicMock()
    checkpointer = MagicMock()

    with patch("src.admin_agent.ChatOpenAI"), patch(
        "src.admin_agent.create_agent") as create_agent_mock:
        create_agent_mock.return_value = MagicMock()
        agent = AdminApprovalAgent(
            _settings(),
            database,
            checkpointer=checkpointer)

    kwargs = create_agent_mock.call_args.kwargs
    assert kwargs["checkpointer"] is checkpointer
    assert len(kwargs["middleware"]) == 2
    assert any(
        middleware.__class__.__name__
        == "HumanInTheLoopMiddleware"
        for middleware in kwargs["middleware"])

    assert {
        tool.name for tool in kwargs["tools"]
    } >= {
        "approve_reservation",
        "refuse_reservation"}
    agent.close()

def test_propose_returns_real_interrupt_details():
    database = MagicMock()
    database.get_admin_review.return_value = {
        "thread_id": "thread-1",
        "reservation": {
            "name": "Anna",
            "surname": "Ponomarenko",
            "car_number": "AA1234BB",
            "period_start": "2026-07-03T10:00:00",
            "period_end": "2026-07-03T12:00:00",
            "status": "pending"}}
    checkpointer = MagicMock()

    with patch("src.admin_agent.ChatOpenAI"), patch(
        "src.admin_agent.create_agent") as create_agent_mock:
        fake_interrupt = SimpleNamespace(
            value={
                "action_requests": [
                    {
                        "name": "approve_reservation",
                        "arguments": {
                            "reservation_id": "r1"}}],
                "review_configs": []})
        fake_result = SimpleNamespace(
            interrupts=(fake_interrupt,))
        fake_graph = MagicMock()
        fake_graph.invoke.return_value = fake_result
        create_agent_mock.return_value = fake_graph

        agent = AdminApprovalAgent(
            _settings(),
            database,
            checkpointer=checkpointer)

    result = agent.propose(
        reservation_id="r1",
        instruction="approve it",
        thread_id="thread-1")

    assert result["status"] == "awaiting_confirmation"
    database.mark_review_awaiting_confirmation.assert_called_once_with(
        thread_id="thread-1",
        proposed_action="approve_reservation")
