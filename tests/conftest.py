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

os.environ.setdefault("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp")
os.environ.setdefault("MCP_ACCESS_TOKEN", "test-mcp-token")
os.environ.setdefault("MCP_JWT_SECRET", "test-secret-that-is-at-least-32-characters")
os.environ.setdefault("MCP_JWT_ISSUER", "citypark-test-auth")
os.environ.setdefault("MCP_JWT_AUDIENCE", "citypark-test-mcp")
os.environ.setdefault("MCP_TIMEOUT_SECONDS", "2")
os.environ.setdefault("MCP_RETRY_ATTEMPTS", "1")
os.environ.setdefault("MCP_HOST", "127.0.0.1")
os.environ.setdefault("MCP_PORT", "8001")
os.environ.setdefault("MCP_OUTPUT_FILE", "storage/test-approved.txt")
os.environ.setdefault("MCP_INDEX_FILE", "storage/test-approved.index.json")