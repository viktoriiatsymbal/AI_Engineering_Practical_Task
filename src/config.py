"""
Configuration loaded from env variables
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv
from sqlalchemy import URL

load_dotenv()

def _require(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    llm_model: str
    embedding_model: str

    weaviate_url: str
    weaviate_api_key: str
    weaviate_class_name: str

    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_sslmode: str

    max_reservation_hours: int

    admin_api_url: str
    admin_api_token: str
    admin_api_timeout_seconds: float

    mcp_server_url: str
    mcp_access_token: str
    mcp_jwt_secret: str
    mcp_jwt_issuer: str
    mcp_jwt_audience: str
    mcp_timeout_seconds: float
    mcp_retry_attempts: int
    mcp_host: str
    mcp_port: int
    mcp_output_file: str
    mcp_index_file: str

    @property
    def postgres_dsn(self):
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
            query={"sslmode": self.postgres_sslmode})

    @property
    def postgres_checkpoint_dsn(self):
        url = URL.create(
            drivername="postgresql",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
            query={"sslmode": self.postgres_sslmode})
        return url.render_as_string(hide_password=False)

def load_settings():
    return Settings(
        openai_api_key=_require("OPENAI_API_KEY"),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        weaviate_url=_require("WEAVIATE_URL"),
        weaviate_api_key=_require("WEAVIATE_API_KEY"),
        weaviate_class_name=os.getenv(
            "WEAVIATE_CLASS_NAME",
            "ParkingStaticInfo"),
        postgres_host=_require("POSTGRES_HOST"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        postgres_db=_require("POSTGRES_DB"),
        postgres_user=_require("POSTGRES_USER"),
        postgres_password=_require("POSTGRES_PASSWORD"),
        postgres_sslmode=os.getenv("POSTGRES_SSLMODE", "require"),
        max_reservation_hours=int(
            os.getenv("MAX_RESERVATION_HOURS", "24")),
        admin_api_url=os.getenv(
            "ADMIN_API_URL",
            "http://127.0.0.1:8000").rstrip("/"),
        admin_api_token=_require("ADMIN_API_TOKEN"),
        admin_api_timeout_seconds=float(
            os.getenv("ADMIN_API_TIMEOUT_SECONDS", "10"))
        mcp_server_url=os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp").rstrip("/"),
        mcp_access_token=os.getenv("MCP_ACCESS_TOKEN", ""),
        mcp_jwt_secret=_require("MCP_JWT_SECRET"),
        mcp_jwt_issuer=os.getenv("MCP_JWT_ISSUER", "citypark-auth"),
        mcp_jwt_audience=os.getenv("MCP_JWT_AUDIENCE", "citypark-mcp"),
        mcp_timeout_seconds=float(os.getenv("MCP_TIMEOUT_SECONDS", "15")),
        mcp_retry_attempts=int(os.getenv("MCP_RETRY_ATTEMPTS", "3")),
        mcp_host=os.getenv("MCP_HOST", "127.0.0.1"),
        mcp_port=int(os.getenv("MCP_PORT", "8001")),
        mcp_output_file=os.getenv("MCP_OUTPUT_FILE", "storage/approved_reservations.txt"),
        mcp_index_file=os.getenv("MCP_INDEX_FILE", "storage/approved_reservations.index.json"))
