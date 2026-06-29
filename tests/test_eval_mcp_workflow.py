from evaluation.eval_mcp_workflow import _summary

def test_summary_calculates_mcp_latency():
    result = _summary([1.0, 2.0, 3.0])
    assert result["mean_seconds"] == 2.0
    assert result["p50_seconds"] == 2.0
    assert result["max_seconds"] == 3.0

def test_summary_handles_no_successful_calls():
    assert _summary([]) == {
        "mean_seconds": 0.0,
        "p50_seconds": 0.0,
        "max_seconds": 0.0}
