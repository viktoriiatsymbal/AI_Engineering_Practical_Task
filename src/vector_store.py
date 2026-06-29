"""
Static data embedded and stored in Weaviate Cloud
"""
import json
import weaviate
from weaviate.auth import Auth
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.classes.config import Configure, DataType, Property
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_weaviate.vectorstores import WeaviateVectorStore

def connect(settings):
    return weaviate.connect_to_weaviate_cloud(
        cluster_url=settings.weaviate_url,
        auth_credentials=Auth.api_key(settings.weaviate_api_key),
        additional_config=AdditionalConfig(
            timeout=Timeout(
                init=30,
                query=60,
                insert=120)))

def ensure_schema(client, class_name):
    if client.collections.exists(class_name):
        return
    client.collections.create(
        name=class_name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="category", data_type=DataType.TEXT),
            Property(name="source_id", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none())

class StaticKnowledgeBase:
    def __init__(self, client, settings):
        self.client = client
        self.settings = settings
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model, api_key=settings.openai_api_key)
        ensure_schema(client, settings.weaviate_class_name)
        self.store = WeaviateVectorStore(
            client=client,
            index_name=settings.weaviate_class_name,
            text_key="text",
            embedding=self.embeddings)

    def ingest_from_json(self, path, guardrails=None):
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)
        texts = [item["text"] for item in items]
        if guardrails is not None:
            texts = guardrails.filter_documents_for_ingestion(texts)
        docs = [
            Document(
                page_content=text,
                metadata={"category": item["category"], "source_id": item["id"]})
            for item, text in zip(items, texts)]
        self.store.add_documents(docs)
        return len(docs)

    def retriever(self, k=4):
        return self.store.as_retriever(search_kwargs={"k": k})

    def similarity_search(self, query, k=4):
        return self.store.similarity_search(query, k=k)

    def close(self):
        self.client.close()
