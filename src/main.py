"""
Entrypoint to talk to the chatbot
"""
from src.config import load_settings
from src.database import Database
from src.guardrails import GuardRails
from src.rag_chain import RAGChain
from src.vector_store import StaticKnowledgeBase, connect
from src.chatbot import ParkingChatbot

def build_chatbot():
    settings = load_settings()
    guardrails = GuardRails()
    db = Database(settings=settings)
    client = connect(settings)
    kb = StaticKnowledgeBase(client, settings)
    rag = RAGChain(settings, kb, db, guardrails)
    bot = ParkingChatbot(settings, rag, db, guardrails)
    return bot, client

def main():
    '''
    Main function to run the chatbot in an interactive loop
    '''
    bot, client = build_chatbot()
    print("CityPark assistant ready. Type 'exit' to quit.")
    try:
        while True:
            message = input("you: ").strip()
            if message.lower() in {"exit", "quit"}:
                break
            if not message:
                continue
            response = bot.handle_message(message)
            print(f"bot: {response}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
