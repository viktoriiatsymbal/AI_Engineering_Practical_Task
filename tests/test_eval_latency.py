from unittest.mock import MagicMock
from evaluation.eval_latency import evaluate_performance

def test_evaluate_performance_success():
    rag = MagicMock()
    rag.retrieve_only.return_value = []
    rag.answer.return_value = "ok"
    result = evaluate_performance(rag, ["q1", "q2"])
    assert result["requests_successful"] == 2
    assert result["success_rate_percent"] == 100.0

def test_evaluate_performance_failure():
    rag = MagicMock()
    rag.retrieve_only.side_effect = RuntimeError("down")
    result = evaluate_performance(rag, ["q1"])
    assert result["requests_successful"] == 0
    assert result["failures"][0]["error_type"] == "RuntimeError"
