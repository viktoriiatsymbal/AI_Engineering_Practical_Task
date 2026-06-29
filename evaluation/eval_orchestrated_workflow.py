"""
Evaluate Stage 4 graph latency and end-to-end path success
"""
import json
import statistics
import time
from pathlib import Path
from src.orchestration.service import build_workflow_service

def run_evaluation(runs=3, output_path="evaluation/results/stage4_results.json"):
    service = build_workflow_service()
    latencies = []
    failures = []
    try:
        for index in range(1, runs + 1):
            started = time.perf_counter()
            try:
                result = service.start(
                    message="What are the parking working hours?",
                    session_id=f"stage4-eval-{index}")
                if result["status"] not in {"completed", "responded"}:
                    raise RuntimeError(f"Unexpected status: {result['status']}")
                latencies.append(time.perf_counter() - started)
            except Exception as exc:
                failures.append({"run": index, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        service.close()

    successful = len(latencies)
    report = {
        "runs_attempted": runs,
        "runs_successful": successful,
        "success_rate_percent": round(successful / runs * 100, 2) if runs else 0,
        "information_workflow_latency_seconds": {
            "mean": round(statistics.mean(latencies), 4) if latencies else None,
            "p50": round(statistics.median(latencies), 4) if latencies else None,
            "max": round(max(latencies), 4) if latencies else None},
        "failures": failures}
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report

if __name__ == "__main__":
    run_evaluation()
