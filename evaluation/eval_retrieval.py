from dataclasses import asdict, dataclass
from src.config import load_settings
from src.vector_store import StaticKnowledgeBase, connect

K = 3
LABELED_QUERIES = [
    {"query": "Where are you located?", "relevant_ids": {"location-1"}},
    {"query": "What documents are required to make a reservation?", "relevant_ids": {"booking-1"}},
    {"query": "Can I cancel my reservation?", "relevant_ids": {"booking-2"}},
    {"query": "Do you have electric vehicle charging?", "relevant_ids": {"details-2"}},
    {"query": "What parking zones do you have?", "relevant_ids": {"details-1"}},
    {"query": "Do you share my personal data with anyone?", "relevant_ids": {"policy-1"}},
    {"query": "Tell me about your facility security.", "relevant_ids": {"general-1"}},
]

@dataclass
class CaseResult:
    query: str
    expected_ids: list[str]
    retrieved_ids: list[str]
    recall_at_k: float
    precision_at_k: float

def evaluate_retrieval(kb, k=K):
    cases = []
    for case in LABELED_QUERIES:
        docs = kb.similarity_search(case["query"], k=k)
        retrieved_ids = [
            doc.metadata.get("source_id")
            for doc in docs
            if doc.metadata.get("source_id")]
        relevant = set(case["relevant_ids"])
        retrieved = set(retrieved_ids)
        hits = retrieved & relevant
        cases.append(
            CaseResult(
                query=case["query"],
                expected_ids=sorted(relevant),
                retrieved_ids=retrieved_ids,
                recall_at_k=len(hits) / len(relevant) if relevant else 0.0,
                precision_at_k=len(hits) / len(retrieved) if retrieved else 0.0))

    return {
        "k": k,
        "query_count": len(cases),
        "average_recall_at_k": sum(c.recall_at_k for c in cases) / len(cases),
        "average_precision_at_k": sum(c.precision_at_k for c in cases) / len(cases),
        "cases": [asdict(c) for c in cases]}

def print_retrieval_results(results):
    k = results["k"]
    print(f"Evaluated {results['query_count']} queries at K={k}")
    for case in results["cases"]:
        print(
            f"  recall={case['recall_at_k']:.2f} "
            f"precision={case['precision_at_k']:.2f}  "
            f"{case['query']}"
        )
    print(f"Average Recall@{k}: {results['average_recall_at_k']:.3f}")
    print(f"Average Precision@{k}: {results['average_precision_at_k']:.3f}")

def main():
    settings = load_settings()
    client = connect(settings)
    try:
        kb = StaticKnowledgeBase(client, settings)
        print_retrieval_results(evaluate_retrieval(kb))
    finally:
        client.close()

if __name__ == "__main__":
    main()
