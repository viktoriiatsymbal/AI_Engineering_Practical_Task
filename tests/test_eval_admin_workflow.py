from unittest.mock import MagicMock
from evaluation.eval_admin_workflow import _summary, evaluate_admin_workflow

def test_summary_calculates_statistics():
    result = _summary([1.0, 2.0, 3.0])
    assert result["mean_seconds"] == 2.0
    assert result["p50_seconds"] == 2.0
    assert result["max_seconds"] == 3.0

def test_workflow_evaluation_reports_success(monkeypatch):
    database = MagicMock()
    database.get_reservation.return_value = {
        "status": "approved"}
    monkeypatch.setattr(
        "evaluation.eval_admin_workflow."
        "_create_evaluation_reservation",
        lambda database, run_number: "r1")

    escalation = MagicMock()
    escalation.raise_for_status.return_value = None

    proposal = MagicMock()
    proposal.raise_for_status.return_value = None
    proposal.json.return_value = {
        "status": "awaiting_confirmation",
        "thread_id": "t1"}

    resume = MagicMock()
    resume.raise_for_status.return_value = None

    client = MagicMock()
    client.post.side_effect = [escalation, proposal, resume]

    result = evaluate_admin_workflow(client, database, runs=1)

    assert result["runs_successful"] == 1
    assert result["success_rate_percent"] == 100.0


def test_workflow_evaluation_records_failure(monkeypatch):
    database = MagicMock()
    monkeypatch.setattr(
        "evaluation.eval_admin_workflow."
        "_create_evaluation_reservation",
        lambda database, run_number: "r1")
    client = MagicMock()
    client.post.side_effect = RuntimeError("offline")

    result = evaluate_admin_workflow(client, database, runs=1)

    assert result["runs_successful"] == 0
    assert result["success_rate_percent"] == 0.0
    assert result["failures"][0]["error_type"] == "RuntimeError"
