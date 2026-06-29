"""
Upload data into Weaviate Cloud
"""
import argparse
from pathlib import Path
from sqlalchemy import text
from src.config import load_settings
from src.database import Database
from src.guardrails import GuardRails
from src.vector_store import StaticKnowledgeBase, connect

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def seed_postgres(db):
    db.create_all()
    seed_sql = (DATA_DIR / "dynamic_seed.sql").read_text(encoding="utf-8")
    with db.engine.begin() as conn:
        existing = conn.execute(text("SELECT COUNT(*) FROM parking_spaces")).scalar()
        if existing:
            print(f"parking_spaces already has {existing} rows, skipping seed")
            return
        for statement in seed_sql.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))
    print("Postgres seeded with dynamic data")

def ingest_static(kb, guardrails, reset):
    if reset:
        kb.client.collections.delete(kb.settings.weaviate_class_name)
        from src.vector_store import ensure_schema
        ensure_schema(kb.client, kb.settings.weaviate_class_name)
    count = kb.ingest_from_json(str(DATA_DIR / "static_data.json"), guardrails=guardrails)
    print(f"Ingested {count} static documents into Weaviate class '{kb.settings.weaviate_class_name}'")

def main():
    '''
    Main function to ingest static and dynamic data into the RAG system
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Drop and recreate the Weaviate class before ingesting")
    args = parser.parse_args()
    settings = load_settings()
    guardrails = GuardRails()
    db = Database(settings=settings)
    seed_postgres(db)
    client = connect(settings)
    try:
        kb = StaticKnowledgeBase(client, settings)
        ingest_static(kb, guardrails=guardrails, reset=args.reset)
    finally:
        client.close()

if __name__ == "__main__":
    main()
