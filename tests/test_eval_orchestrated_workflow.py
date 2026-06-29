from unittest.mock import Mock
from evaluation import eval_orchestrated_workflow as module

def test_evaluation_reports_success(tmp_path, monkeypatch):
    service = Mock()
    service.start.return_value = {"status": "completed"}
    monkeypatch.setattr(module, "build_workflow_service", lambda: service)

    report = module.run_evaluation(2, tmp_path / "result.json")

    assert report["runs_successful"] == 2
    assert report["success_rate_percent"] == 100.0

def test_evaluation_captures_failures(tmp_path, monkeypatch):
    service = Mock()
    service.start.side_effect = RuntimeError("boom")
    monkeypatch.setattr(module, "build_workflow_service", lambda: service)

    report = module.run_evaluation(1, tmp_path / "result.json")

    assert report["runs_successful"] == 0
    assert report["failures"][0]["error"].startswith("RuntimeError")
