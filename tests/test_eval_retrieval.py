from unittest.mock import MagicMock
from langchain_core.documents import Document
from evaluation.eval_retrieval import evaluate_retrieval

def test_evaluate_retrieval_returns_summary():
    kb = MagicMock()
    kb.similarity_search.return_value = [
        Document(page_content="x", metadata={"source_id": "location-1"})]
    result = evaluate_retrieval(kb, k=3)
    assert result["query_count"] == 7
    assert len(result["cases"]) == 7

def test_evaluate_retrieval_uses_requested_k():
    kb = MagicMock()
    kb.similarity_search.return_value = []
    result = evaluate_retrieval(kb, k=2)
    assert result["k"] == 2
    assert all(call.kwargs["k"] == 2 for call in kb.similarity_search.call_args_list)
