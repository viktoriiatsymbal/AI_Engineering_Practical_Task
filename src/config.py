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
            os.getenv("MAX_RESERVATION_HOURS", "24")))
