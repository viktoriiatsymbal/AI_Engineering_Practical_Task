import json
import platform
from datetime import datetime, timezone
from pathlib import Path
import langchain
from evaluation.eval_latency import evaluate_performance
from evaluation.eval_retrieval import evaluate_retrieval
from src.config import load_settings
from src.database import Database
from src.guardrails import GuardRails
from src.rag_chain import RAGChain
from src.vector_store import StaticKnowledgeBase, connect

RESULTS_DIR = Path(__file__).resolve().parent / "results"

def _sec(value):
    return f"{value:.3f} s"

def build_markdown(payload):
    retrieval = payload["retrieval"]
    perf = payload["performance"]
    k = retrieval["k"]
    rlat = perf["retrieval_latency"]
    alat = perf["full_answer_latency"]

    lines = [
        "# Stage 1 Evaluation Report",
        "",
        f"**Generated:** {payload['generated_at_utc']}",
        "",
        "## Scope",
        "",
        "This report evaluates retrieval quality and system performance for the Stage 1 RAG parking chatbot.",
        "",
        "## Environment",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Python | {payload['environment']['python']} |",
        f"| LangChain | {payload['environment']['langchain']} |",
        f"| LLM model | {payload['environment']['llm_model']} |",
        f"| Embedding model | {payload['environment']['embedding_model']} |",
        f"| Weaviate collection | {payload['environment']['weaviate_class_name']} |",
        "",
        "## Retrieval quality",
        "",
        f"Evaluated {retrieval['query_count']} labelled queries at K={k}.",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Average Recall@{k} | {retrieval['average_recall_at_k']:.3f} |",
        f"| Average Precision@{k} | {retrieval['average_precision_at_k']:.3f} |",
        "",
        "### Per-query results",
        "",
        "| Query | Expected | Retrieved | Recall | Precision |",
        "|---|---|---|---:|---:|"]

    for case in retrieval["cases"]:
        lines.append(
            f"| {case['query']} | {', '.join(case['expected_ids'])} | "
            f"{', '.join(case['retrieved_ids'])} | "
            f"{case['recall_at_k']:.2f} | {case['precision_at_k']:.2f} |")

    lines += [
        "",
        "## Performance",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Requests attempted | {perf['requests_attempted']} |",
        f"| Requests successful | {perf['requests_successful']} |",
        f"| Success rate | {perf['success_rate_percent']:.1f}% |",
        f"| Throughput | {perf['throughput_requests_per_second']:.3f} requests/s |",
        f"| Total test duration | {_sec(perf['total_test_duration_seconds'])} |",
        "",
        "### Retrieval latency",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Mean | {_sec(rlat['mean_seconds'])} |",
        f"| P50 | {_sec(rlat['p50_seconds'])} |",
        f"| P90 | {_sec(rlat['p90_seconds'])} |",
        f"| P95 | {_sec(rlat['p95_seconds'])} |",
        f"| Maximum | {_sec(rlat['max_seconds'])} |",
        "",
        "### Full answer latency",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Mean | {_sec(alat['mean_seconds'])} |",
        f"| P50 | {_sec(alat['p50_seconds'])} |",
        f"| P90 | {_sec(alat['p90_seconds'])} |",
        f"| P95 | {_sec(alat['p95_seconds'])} |",
        f"| Maximum | {_sec(alat['max_seconds'])} |",
        "",
        "## Interpretation",
        "",
        f"- Recall@{k} measures whether the expected source appears among the top {k} retrieved documents.",
        f"- Precision@{k} measures how many retrieved documents are labelled relevant.",
        f"- With one labelled relevant source and K={k}, one correct result gives precision {1/k:.3f}.",
        "- Retrieval latency measures vector search only.",
        "- Full answer latency includes retrieval, SQL context, LangChain agent execution, model generation and PII filtering.",
        "",
        "## Conclusion",
        "",
        (
            "All requests completed successfully in this run."
            if perf["requests_successful"] == perf["requests_attempted"]
            else "Some requests failed. See the JSON report for failure details."),
        "",
        "## Reproduction",
        "",
        "```bash",
        "python -m evaluation.generate_report",
        "```",
        ""]

    return "\n".join(lines)

def main():
    settings = load_settings()
    guardrails = GuardRails()
    db = Database(settings=settings)
    client = connect(settings)

    try:
        kb = StaticKnowledgeBase(client, settings)
        rag = RAGChain(settings, kb, db, guardrails)
        payload = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "environment": {
                "python": platform.python_version(),
                "langchain": getattr(langchain, "__version__", "unknown"),
                "llm_model": settings.llm_model,
                "embedding_model": settings.embedding_model,
                "weaviate_class_name": settings.weaviate_class_name,
            },
            "retrieval": evaluate_retrieval(kb),
            "performance": evaluate_performance(rag)}

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        json_path = RESULTS_DIR / "evaluation_results.json"
        md_path = RESULTS_DIR / "evaluation_report.md"
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        md_path.write_text(build_markdown(payload), encoding="utf-8")
        print(f"JSON results: {json_path}")
        print(f"Markdown report: {md_path}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
