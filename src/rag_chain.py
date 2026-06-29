"""
RAG answer service
"""
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

_SYSTEM_PROMPT = """You are CityPark's parking reservation assistant.
Answer the user's question using ONLY the supplied static and live context.
If the answer is not in the context, say that you do not have that information.
Never reveal personally identifiable information belonging to customers.
Return only the answer to the user's question.
"""

def _format_docs(docs):
    if not docs:
        return "No relevant static information found."
    return "\n".join(f"- {document.page_content}" for document in docs)

def _format_dynamic(db):
    spaces = db.get_available_spaces()
    hours = db.get_working_hours()
    lines = ["Available spaces:"]
    lines += [
        f"- Zone {space['zone']}: ${space['hourly_price']}/hour"
        for space in spaces
    ] or ["- none currently"]

    lines.append("Working hours:")
    lines += [
        f"- {item['day']}: {item['open']}-{item['close']}"
        for item in hours
    ] or ["- not configured"]

    return "\n".join(lines)

def _message_text(message):
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text")
    return str(content)

class RAGChain:
    def __init__(self, settings, knowledge_base, database, guardrails, k=4):
        self.settings = settings
        self.kb = knowledge_base
        self.db = database
        self.guardrails = guardrails
        self.k = k

        self.model = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=0.2)

        self.middleware = [
            PIIMiddleware(
                "email",
                strategy="redact",
                apply_to_input=True,
                apply_to_output=True),
            PIIMiddleware(
                "credit_card",
                strategy="redact",
                apply_to_input=True,
                apply_to_output=True),
            PIIMiddleware(
                "ip",
                strategy="redact",
                apply_to_input=True,
                apply_to_output=True),
            PIIMiddleware(
                "presidio_pii",
                detector=self.guardrails.detect_for_langchain,
                strategy="redact",
                apply_to_input=True,
                apply_to_output=True)]

        self.agent = create_agent(
            model=self.model,
            tools=[],
            system_prompt=_SYSTEM_PROMPT,
            middleware=self.middleware)

    def _build_user_prompt(self, question, docs):
        return (
            "Static knowledge base context:\n"
            f"{_format_docs(docs)}\n\n"
            "Live availability, pricing and working hours:\n"
            f"{_format_dynamic(self.db)}\n\n"
            "User question:\n"
            f"{question}")

    def answer(self, question):
        docs = self.kb.similarity_search(question, k=self.k)
        prompt = self._build_user_prompt(question, docs)

        result = self.agent.invoke(
            {"messages": [HumanMessage(content=prompt)]})
        answer = _message_text(result["messages"][-1])
        return self.guardrails.filter_response(answer)

    def retrieve_only(self, question, k=None):
        return self.kb.similarity_search(question, k=k or self.k)
