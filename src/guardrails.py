"""
Protection against sensitive data leakage
"""
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

_DEFAULT_ENTITIES = [
    "PERSON",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "CREDIT_CARD",
    "IBAN_CODE",
    "US_SSN",
    "LOCATION",
]

_PUBLIC_CONTENT_EXCLUDED_ENTITIES = {"LOCATION"}

class GuardRails:
    def __init__(self, entities=None, language="en"):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.entities = entities or _DEFAULT_ENTITIES
        self.language = language

    def detect(self, text, excluded_entities=None):
        excluded = set(excluded_entities or [])
        entities = [entity for entity in self.entities if entity not in excluded]
        return self.analyzer.analyze(
            text=text,
            entities=entities,
            language=self.language)

    def contains_sensitive_data(self, text, excluded_entities=None):
        return bool(self.detect(text, excluded_entities=excluded_entities))

    def redact(self, text, excluded_entities=None):
        results = self.detect(text, excluded_entities=excluded_entities)
        if not results:
            return text
        return self.anonymizer.anonymize(
            text=text,
            analyzer_results=results).text

    def redact_public_content(self, text):
        return self.redact(
            text,
            excluded_entities=list(_PUBLIC_CONTENT_EXCLUDED_ENTITIES))

    def filter_documents_for_ingestion(self, texts):
        """Remove detected PII before embedding and storing documents in Weaviate."""
        return [self.redact_public_content(text) for text in texts]

    def filter_response(self, text):
        """Defense-in-depth filter for callers outside the LangChain agent."""
        return self.redact_public_content(text)

    def detect_for_langchain(self, content):
        """Return Presidio matches in the format required by LangChain PIIMiddleware.

        LOCATION is excluded because CityPark's public business address is legitimate
        RAG content. Customer names, phone numbers, emails, financial identifiers and
        similar supported entities are still detected.
        """
        results = self.detect(
            content,
            excluded_entities=list(_PUBLIC_CONTENT_EXCLUDED_ENTITIES))
        return [
            {
                "text": content[result.start:result.end],
                "start": result.start,
                "end": result.end,
            }
            for result in results]
