import json
from unittest.mock import MagicMock, patch
from src.config import load_settings

def make_kb(tmp_path, mocker):
    settings = load_settings()
    fake_client = MagicMock()
    fake_client.collections.exists.return_value = True
    with patch("src.vector_store.OpenAIEmbeddings"), patch(
        "src.vector_store.WeaviateVectorStore"
    ) as mock_store_cls:
        from src.vector_store import StaticKnowledgeBase
        kb = StaticKnowledgeBase(fake_client, settings)
        return kb, mock_store_cls.return_value

def test_ensure_schema_skips_creation_when_class_exists():
    from src.vector_store import ensure_schema
    fake_client = MagicMock()
    fake_client.collections.exists.return_value = True
    ensure_schema(fake_client, "ParkingStaticInfo")
    fake_client.collections.create.assert_not_called()

def test_ensure_schema_creates_class_when_missing():
    from src.vector_store import ensure_schema
    fake_client = MagicMock()
    fake_client.collections.exists.return_value = False
    ensure_schema(fake_client, "ParkingStaticInfo")
    fake_client.collections.create.assert_called_once()

def test_ingest_from_json_applies_guardrails(tmp_path, mocker):
    kb, mock_store = make_kb(tmp_path, mocker)
    data = [{"id": "x1", "category": "general", "text": "call me at 555-000-1111"}]
    path = tmp_path / "static.json"
    path.write_text(json.dumps(data))
    fake_guardrails = MagicMock()
    fake_guardrails.filter_documents_for_ingestion.return_value = ["call me at <PHONE_NUMBER>"]
    count = kb.ingest_from_json(str(path), guardrails=fake_guardrails)

    assert count == 1
    fake_guardrails.filter_documents_for_ingestion.assert_called_once_with(
        ["call me at 555-000-1111"])
    mock_store.add_documents.assert_called_once()

def test_retriever_delegates_to_store(tmp_path, mocker):
    kb, mock_store = make_kb(tmp_path, mocker)
    kb.retriever(k=2)
    mock_store.as_retriever.assert_called_once_with(search_kwargs={"k": 2})
