"""
Entrypoint to talk to the chatbot with escalation enabled
"""
from src.admin_client import AdminClient
from src.chatbot import ParkingChatbot
from src.config import load_settings
from src.database import Database
from src.guardrails import GuardRails
from src.rag_chain import RAGChain
from src.vector_store import StaticKnowledgeBase, connect

def build_chatbot():
    settings = load_settings()
    guardrails = GuardRails()
    database = Database(settings=settings)
    client = connect(settings)
    knowledge_base = StaticKnowledgeBase(client, settings)
    rag = RAGChain(
        settings,
        knowledge_base,
        database,
        guardrails)
    admin_client = AdminClient(
        base_url=settings.admin_api_url,
        token=settings.admin_api_token,
        timeout_seconds=settings.admin_api_timeout_seconds)
    bot = ParkingChatbot(
        settings,
        rag,
        database,
        guardrails,
        admin_client=admin_client)
    return bot, client

def main():
    bot, client = build_chatbot()
    print("CityPark assistant ready. Type 'exit' to quit.")
    try:
        while True:
            message = input("you: ").strip()
            if message.lower() in {"exit", "quit"}:
                break
            if not message:
                continue
            print(f"bot: {bot.handle_message(message)}")
    finally:
        bot.close()
        client.close()

if __name__ == "__main__":
    main()
