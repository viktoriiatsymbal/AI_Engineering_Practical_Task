import json
import os
import statistics
import time
from datetime import datetime, timedelta
from pathlib import Path
import httpx
from src.config import load_settings
from src.database import Database

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DEFAULT_RUNS = 3

def _summary(values):
    if not values:
        return {
            "mean_seconds": 0.0,
            "p50_seconds": 0.0,
            "max_seconds": 0.0}
    return {
        "mean_seconds": statistics.mean(values),
        "p50_seconds": statistics.median(values),
        "max_seconds": max(values)}

def _create_evaluation_reservation(database, run_number):
    spaces = database.get_available_spaces()
    if not spaces:
        raise RuntimeError("No available parking spaces for evaluation")

    start = (
        datetime.now() + timedelta(days=7 + run_number)
    ).replace(hour=10, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=2)

    return database.create_reservation(
        parking_space_id=spaces[0]["id"],
        name="Evaluation",
        surname=f"Run{run_number}",
        car_number=f"EV{run_number:04d}",
        period_start=start,
        period_end=end)

def evaluate_admin_workflow(client, database, runs=DEFAULT_RUNS):
    escalation, proposal, resume, failures = [], [], [], []

    for run_number in range(1, runs + 1):
        reservation_id = None
        try:
            reservation_id = _create_evaluation_reservation(
                database, run_number)
            started = time.perf_counter()
            response = client.post(
                "/admin/requests",
                json={"reservation_id": reservation_id})
            response.raise_for_status()
            escalation.append(time.perf_counter() - started)

            started = time.perf_counter()
            response = client.post(
                "/admin/commands",
                json={
                    "reservation_id": reservation_id,
                    "instruction": "Approve this reservation"})
            response.raise_for_status()
            body = response.json()
            proposal.append(time.perf_counter() - started)

            if body.get("status") != "awaiting_confirmation":
                raise RuntimeError(
                    "Admin agent did not produce a HITL interrupt")

            started = time.perf_counter()
            response = client.post(
                "/admin/decisions",
                json={
                    "thread_id": body["thread_id"],
                    "decision": "approve",
                    "message": None})
            response.raise_for_status()
            resume.append(time.perf_counter() - started)

            reservation = database.get_reservation(reservation_id)
            if reservation["status"] != "approved":
                raise RuntimeError(
                    "Reservation was not approved after HITL resume")

        except Exception as exc:
            failures.append(
                {
                    "run": run_number,
                    "reservation_id": reservation_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc)})

    successful = runs - len(failures)
    return {
        "runs_attempted": runs,
        "runs_successful": successful,
        "success_rate_percent": (
            successful / runs * 100 if runs else 0.0),
        "request_escalation_latency": _summary(escalation),
        "admin_agent_proposal_latency": _summary(proposal),
        "resume_latency": _summary(resume),
        "failures": failures}

def print_results(results):
    print(f"Runs attempted: {results['runs_attempted']}")
    print(f"Runs successful: {results['runs_successful']}")
    print(f"Success rate: {results['success_rate_percent']:.1f}%")

    for label, key in (
        ("Request escalation latency", "request_escalation_latency"),
        ("Admin-agent proposal latency", "admin_agent_proposal_latency"),
        ("HITL resume latency", "resume_latency")):
        metrics = results[key]
        print(f"\n{label}:")
        print(f"  Mean: {metrics['mean_seconds']:.3f}s")
        print(f"  P50: {metrics['p50_seconds']:.3f}s")
        print(f"  Max: {metrics['max_seconds']:.3f}s")

def main():
    settings = load_settings()
    database = Database(settings=settings)
    runs = int(
        os.getenv("ADMIN_WORKFLOW_EVAL_RUNS", DEFAULT_RUNS))

    with httpx.Client(
        base_url=settings.admin_api_url,
        headers={
            "Authorization": f"Bearer {settings.admin_api_token}"},
        timeout=max(settings.admin_api_timeout_seconds, 60.0)) as client:
        results = evaluate_admin_workflow(
            client=client,
            database=database,
            runs=runs)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / "admin_workflow_results.json"
    output_path.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8")
    print_results(results)
    print(f"\nJSON results: {output_path}")

if __name__ == "__main__":
    main()
