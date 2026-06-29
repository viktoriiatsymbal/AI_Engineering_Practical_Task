import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("WEAVIATE_URL", "https://test.weaviate.network")
os.environ.setdefault("WEAVIATE_API_KEY", "test-key")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_SSLMODE", "disable")

os.environ.setdefault("ADMIN_API_URL", "http://127.0.0.1:8000")
os.environ.setdefault("ADMIN_API_TOKEN", "test-admin-token")
os.environ.setdefault("ADMIN_API_TIMEOUT_SECONDS", "2")