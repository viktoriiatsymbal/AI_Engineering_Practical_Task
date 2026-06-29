from src.guardrails import GuardRails

def test_detects_email_and_phone_number():
    guardrails = GuardRails()
    text = "Contact me at john.doe@example.com or call 555-123-4567."

    assert guardrails.contains_sensitive_data(text)

def test_clean_text_has_no_sensitive_data():
    guardrails = GuardRails()
    text = "What are your working hours on weekends?"

    assert not guardrails.contains_sensitive_data(text)

def test_redact_replaces_pii_with_placeholder():
    guardrails = GuardRails()
    text = "My name is John Smith."
    redacted = guardrails.redact(text)

    assert "John Smith" not in redacted
    assert "<PERSON>" in redacted

def test_filter_documents_for_ingestion_redacts_each_text():
    guardrails = GuardRails()
    texts = [
        "General parking info.",
        "Email me at jane@example.com for details."]
    filtered = guardrails.filter_documents_for_ingestion(texts)

    assert filtered[0] == texts[0]
    assert "jane@example.com" not in filtered[1]

def test_presidio_detector_returns_langchain_match_format():
    guardrails = GuardRails()
    matches = guardrails.detect_for_langchain(
        "Contact John Smith at john@example.com.")

    assert matches
    assert all({"text", "start", "end"} <= match.keys() for match in matches)
    for match in matches:
        assert isinstance(match["start"], int)
        assert isinstance(match["end"], int)
        assert match["text"]
