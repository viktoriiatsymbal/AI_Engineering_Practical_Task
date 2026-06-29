"""
Measure MCP recording latency and success rate
"""
import json
import os
import statistics
import time
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from src.config import load_settings
from src.database import Database
from src.mcp_client import MCPReservationRecorder

RESULTS_DIR = Path(__file__).resolve().parent / "results"

def _summary(values):
    if not values:
        return {"mean_seconds": 0.0, "p50_seconds": 0.0, "max_seconds": 0.0}
    return {
        "mean_seconds": statistics.mean(values),
        "p50_seconds": statistics.median(values),
        "max_seconds": max(values)}

def evaluate(runs=3):
    settings = load_settings()
    database = Database(settings=settings)
    recorder = MCPReservationRecorder(settings)
    latencies, failures = [], []

    spaces = database.get_available_spaces()
    if not spaces:
        raise RuntimeError("No parking spaces available for evaluation")

    for number in range(1, runs + 1):
        reservation_id = None
        try:
            start = (datetime.now() + timedelta(days=30 + number)).replace(
                hour=10, minute=0, second=0, microsecond=0)
            reservation_id = database.create_reservation(
                parking_space_id=spaces[0]["id"],
                name="MCP",
                surname=f"Evaluation{number}",
                car_number=f"MC{number:04d}",
                period_start=start,
                period_end=start + timedelta(hours=1))
            database.create_admin_review(reservation_id, str(uuid4()))
            database.resolve_admin_review(reservation_id, "approved", "MCP evaluation")

            before = time.perf_counter()
            recorder.record(reservation_id)
            latencies.append(time.perf_counter() - before)
        except Exception as exc:
            failures.append(
                {
                    "run": number,
                    "reservation_id": reservation_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc)})

    successful = runs - len(failures)
    return {
        "runs_attempted": runs,
        "runs_successful": successful,
        "success_rate_percent": successful / runs * 100 if runs else 0.0,
        "mcp_recording_latency": _summary(latencies),
        "failures": failures}

def main():
    results = evaluate(int(os.getenv("MCP_EVAL_RUNS", "3")))
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / "mcp_workflow_results.json"
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"JSON results: {path}")

if __name__ == "__main__":
    main()
