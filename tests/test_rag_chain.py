from unittest.mock import MagicMock, patch
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from src.config import load_settings
from src.database import Database
from src.guardrails import GuardRails
from src.rag_chain import RAGChain, _format_docs, _format_dynamic

def test_format_docs_with_documents():
    docs = [
        Document(page_content="Located downtown."),
        Document(page_content="Open 24/7.")]
    formatted = _format_docs(docs)

    assert "Located downtown." in formatted
    assert "Open 24/7." in formatted

def test_format_docs_empty_list():
    assert _format_docs([]) == "No relevant static information found."

def test_format_dynamic_includes_spaces_and_hours():
    from datetime import time
    from src.database import ParkingSpace, WorkingHours

    db = Database(dsn="sqlite:///:memory:")
    db.create_all()

    with db.session() as session:
        session.add(
            ParkingSpace(zone="A", is_available=True, hourly_price=2.5))
        session.add(
            WorkingHours(
                day_of_week="Monday",
                open_time=time(7, 0),
                close_time=time(23, 0)))
    formatted = _format_dynamic(db)

    assert "Zone A" in formatted
    assert "Monday" in formatted


def test_rag_chain_creates_real_langchain_agent_with_pii_middleware():
    settings = load_settings()
    db = Database(dsn="sqlite:///:memory:")
    db.create_all()
    fake_kb = MagicMock()
    guardrails = MagicMock(spec=GuardRails)

    with patch("src.rag_chain.ChatOpenAI"), patch(
        "src.rag_chain.create_agent"
    ) as create_agent_mock:
        create_agent_mock.return_value = MagicMock()
        chain = RAGChain(settings, fake_kb, db, guardrails)

    create_agent_mock.assert_called_once()
    kwargs = create_agent_mock.call_args.kwargs
    assert kwargs["tools"] == []
    assert kwargs["middleware"] == chain.middleware
    assert len(chain.middleware) >= 4
    assert any(
        middleware.__class__.__name__ == "PIIMiddleware"
        for middleware in chain.middleware)

def test_rag_chain_invokes_guarded_agent_and_filters_final_response():
    settings = load_settings()
    db = Database(dsn="sqlite:///:memory:")
    db.create_all()
    fake_kb = MagicMock()
    fake_kb.similarity_search.return_value = [
        Document(page_content="CityPark is downtown.")]

    fake_guardrails = MagicMock(spec=GuardRails)
    fake_guardrails.detect_for_langchain.return_value = []
    fake_guardrails.filter_response.return_value = (
        "Contact customer at <EMAIL_ADDRESS>.")

    fake_agent = MagicMock()
    fake_agent.invoke.return_value = {
        "messages": [
            AIMessage(content="Contact customer at john@example.com.")]}

    with patch("src.rag_chain.ChatOpenAI"), patch(
        "src.rag_chain.create_agent",
        return_value=fake_agent):
        chain = RAGChain(settings, fake_kb, db, fake_guardrails)
    response = chain.answer("Where is CityPark?")
    fake_kb.similarity_search.assert_called_once_with(
        "Where is CityPark?",
        k=4)
    fake_agent.invoke.assert_called_once()
    fake_guardrails.filter_response.assert_called_once_with(
        "Contact customer at john@example.com.")
    assert "john@example.com" not in response
