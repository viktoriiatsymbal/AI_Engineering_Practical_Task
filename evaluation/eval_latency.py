import statistics
import time
from src.config import load_settings
from src.database import Database
from src.guardrails import GuardRails
from src.rag_chain import RAGChain
from src.vector_store import StaticKnowledgeBase, connect

QUESTIONS = [
    "Where is CityPark located?",
    "What do I need to make a reservation?",
    "Do you have EV charging?",
    "What are your working hours?",
    "What zones do you have and what do they cost?",
] * 3

def _percentile(values, p):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    rank = (p / 100) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1 - weight) + ordered[high] * weight

def _summary(values):
    if not values:
        return {k: 0.0 for k in (
            "mean_seconds", "p50_seconds", "p90_seconds",
            "p95_seconds", "max_seconds")}
    return {
        "mean_seconds": statistics.mean(values),
        "p50_seconds": statistics.median(values),
        "p90_seconds": _percentile(values, 90),
        "p95_seconds": _percentile(values, 95),
        "max_seconds": max(values)}

def evaluate_performance(rag, questions=None):
    questions = questions or QUESTIONS
    retrieval_times, answer_times, failures = [], [], []
    total_start = time.perf_counter()

    for question in questions:
        try:
            start = time.perf_counter()
            rag.retrieve_only(question)
            retrieval_times.append(time.perf_counter() - start)
            start = time.perf_counter()
            rag.answer(question)
            answer_times.append(time.perf_counter() - start)
        except Exception as exc:
            failures.append({
                "question": question,
                "error_type": type(exc).__name__,
                "error": str(exc)})

    total_seconds = time.perf_counter() - total_start
    attempted = len(questions)
    successful = attempted - len(failures)

    return {
        "requests_attempted": attempted,
        "requests_successful": successful,
        "success_rate_percent": successful / attempted * 100 if attempted else 0.0,
        "throughput_requests_per_second": successful / total_seconds if total_seconds else 0.0,
        "total_test_duration_seconds": total_seconds,
        "retrieval_latency": _summary(retrieval_times),
        "full_answer_latency": _summary(answer_times),
        "failures": failures}

def print_performance_results(results):
    print(f"Requests attempted: {results['requests_attempted']}")
    print(f"Requests successful: {results['requests_successful']}")
    print(f"Success rate: {results['success_rate_percent']:.1f}%")
    print(f"Throughput: {results['throughput_requests_per_second']:.3f} requests/second")

    for title, key in (
        ("Retrieval latency", "retrieval_latency"),
        ("Full answer latency", "full_answer_latency")):
        metrics = results[key]
        print(f"\n{title}:")
        print(f"  Mean: {metrics['mean_seconds']:.3f}s")
        print(f"  P50: {metrics['p50_seconds']:.3f}s")
        print(f"  P90: {metrics['p90_seconds']:.3f}s")
        print(f"  P95: {metrics['p95_seconds']:.3f}s")
        print(f"  Max: {metrics['max_seconds']:.3f}s")

def main():
    settings = load_settings()
    guardrails = GuardRails()
    db = Database(settings=settings)
    client = connect(settings)
    try:
        kb = StaticKnowledgeBase(client, settings)
        rag = RAGChain(settings, kb, db, guardrails)
        print_performance_results(evaluate_performance(rag))
    finally:
        client.close()

if __name__ == "__main__":
    main()
