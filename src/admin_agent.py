"""
Second LangChain agent for administrator review with HITL middleware
"""
from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware, wrap_model_call)
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from src.admin_tools import build_admin_tools

_SYSTEM_PROMPT = """You are CityPark's administrator approval agent.

You only handle existing pending reservation reviews.

Rules:
1. First inspect the reservation with get_reservation_details when needed.
2. If the administrator asks to approve, call approve_reservation exactly once.
3. If the administrator asks to refuse, call refuse_reservation exactly once.
4. Never invent a reservation ID or change reservation data.
5. Never claim that a reservation was changed unless the tool completed.
6. Side-effecting tools are protected by HumanInTheLoopMiddleware and must pause
   for the administrator's explicit confirmation.
"""

@wrap_model_call
def force_admin_action_tool(request, handler):
    """
    Force the administrator agent to select an action tool
    on the first model call.

    After the tool has executed, the model may return a normal
    final response without being forced to call another tool.
    """
    messages = request.state.get("messages", [])

    if not messages:
        return handler(request)

    last_message = messages[-1]
    last_message_type = getattr(last_message, "type", None)

    if last_message_type == "human":
        forced_model = request.model.bind_tools(
            request.tools,
            tool_choice="required")
        return handler(
            request.override(model=forced_model))

    return handler(request)

class AdminApprovalAgent:
    def __init__(self, settings, database, checkpointer=None):
        self.settings = settings
        self.database = database
        self._checkpointer_cm = None

        if checkpointer is None:
            self._checkpointer_cm = PostgresSaver.from_conn_string(
                settings.postgres_checkpoint_dsn)
            checkpointer = self._checkpointer_cm.__enter__()
            checkpointer.setup()

        self.checkpointer = checkpointer
        all_tools = build_admin_tools(database)

        self.tools = [
            tool
            for tool in all_tools
            if tool.name
            in {
                "approve_reservation",
                "refuse_reservation"}]
        self.model = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=0)

        self.agent = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=_SYSTEM_PROMPT,
            middleware=[
                force_admin_action_tool,
                HumanInTheLoopMiddleware(
                    interrupt_on={
                        "approve_reservation": {
                            "allowed_decisions": [
                                "approve",
                                "reject"],
                            "description": (
                                "Confirm execution of reservation approval")},
                        "refuse_reservation": {
                            "allowed_decisions": [
                                "approve",
                                "reject"],
                            "description": (
                                "Confirm execution of reservation refusal")}},
                    description_prefix=(
                        "Administrator confirmation required"))],
            checkpointer=self.checkpointer)

    @staticmethod
    def _config(thread_id):
        return {"configurable": {"thread_id": thread_id}}

    def propose(self, reservation_id, instruction, thread_id):
        review = self.database.get_admin_review(
            reservation_id)
        if review is None:
            raise KeyError(
                f"Reservation review not found: "
                f"{reservation_id}")

        reservation = review["reservation"]

        prompt = (
            "You must execute exactly one administrator "
            "decision tool.\n\n"
            f"Reservation ID: {reservation_id}\n"
            f"Customer: {reservation['name']} "
            f"{reservation['surname']}\n"
            f"Car number: {reservation['car_number']}\n"
            f"Period: {reservation['period_start']} "
            f"to {reservation['period_end']}\n"
            f"Current status: {reservation['status']}\n\n"
            f"Administrator instruction: {instruction}\n\n"
            "Choose exactly one tool:\n"
            "- approve_reservation, if the administrator "
            "wants approval;\n"
            "- refuse_reservation, if the administrator "
            "wants refusal.\n"
            "Do not answer only with text.")

        result = self.agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt}]},
            config=self._config(thread_id),
            version="v2")

        if not result.interrupts:
            raise RuntimeError(
                "The administrator agent did not propose "
                "an approval or refusal tool call.")

        interrupt_value = result.interrupts[0].value

        action_requests = interrupt_value.get(
            "action_requests",
            [])

        if not action_requests:
            raise RuntimeError(
                "The HITL interrupt did not contain "
                "an action request.")

        proposed_action = action_requests[0].get("name")

        if proposed_action not in {
            "approve_reservation",
            "refuse_reservation"}:
            raise RuntimeError(
                f"Unexpected administrator action: "
                f"{proposed_action}")

        self.database.mark_review_awaiting_confirmation(
            thread_id=thread_id,
            proposed_action=proposed_action)

        return {
            "status": "awaiting_confirmation",
            "thread_id": thread_id,
            "reservation_id": reservation_id,
            "action_requests": action_requests,
            "review_configs": interrupt_value.get(
                "review_configs", 
                [])}

    def resume(self, thread_id, decision, message=None):
        if decision not in {"approve", "reject"}:
            raise ValueError(
                "HITL decision must be 'approve' or 'reject'")

        decision_payload = {"type": decision}
        if decision == "reject" and message:
            decision_payload["message"] = message

        result = self.agent.invoke(
            Command(
                resume={"decisions": [decision_payload]}),
            config=self._config(thread_id),
            version="v2")

        return {
            "status": (
                "awaiting_confirmation"
                if result.interrupts
                else "completed"),
            "thread_id": thread_id}

    def close(self):
        if self._checkpointer_cm is not None:
            self._checkpointer_cm.__exit__(None, None, None)
            self._checkpointer_cm = None
