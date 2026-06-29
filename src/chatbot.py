"""
Conversation orchestration for information requests and parking reservations
"""
import re
from datetime import datetime
from typing import Optional, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from src.reservation_validator import ReservationValidator

_REQUIRED_SLOTS = ["name", "surname", "car_number", "period_start", "period_end"]

_INTENT_PROMPT = (
    "Classify the user's message as exactly one word: 'reservation' if they want to book "
    "or reserve a parking space, otherwise 'info'. Message: {message}"
)

_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2})")
_CAR_RE = re.compile(r"\b([A-Z]{1,3}[- ]?\d{3,4}[A-Z]{0,2})\b")
_WORD_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ'’-]+$")

_RESET_COMMANDS = {
    "cancel",
    "cancel reservation",
    "restart",
    "start over",
    "new reservation",
}

class ChatState(TypedDict, total=False):
    message: str
    session_id: str
    route: str
    intent: str
    slots: dict
    reservation_id: Optional[str]
    response: str

class ParkingChatbot:
    def __init__(self, settings, rag_chain, database, guardrails):
        self.settings = settings
        self.rag_chain = rag_chain
        self.db = database
        self.guardrails = guardrails
        self.validator = ReservationValidator(
            database=database,
            max_duration_hours=settings.max_reservation_hours)
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=0)
        self._sessions: dict[str, dict] = {}
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(ChatState)
        graph.add_node("route_request", self._route_request)
        graph.add_node("reset_session", self._reset_session)
        graph.add_node("restart_reservation", self._restart_reservation)
        graph.add_node("classify_intent", self._classify_intent)
        graph.add_node("answer_info", self._answer_info)
        graph.add_node("collect_reservation", self._collect_reservation_node)
        graph.set_entry_point("route_request")
        graph.add_conditional_edges(
            "route_request",
            lambda state: state["route"],
            {
                "reset": "reset_session",
                "restart_reservation": "restart_reservation",
                "continue_reservation": "collect_reservation",
                "classify": "classify_intent"})

        graph.add_conditional_edges(
            "classify_intent",
            lambda state: state["intent"],
            {
                "info": "answer_info",
                "reservation": "collect_reservation"})

        graph.add_edge("reset_session", END)
        graph.add_edge("restart_reservation", END)
        graph.add_edge("answer_info", END)
        graph.add_edge("collect_reservation", END)
        return graph.compile()

    def _route_request(self, state):
        message = state["message"].strip().lower()
        session_id = state["session_id"]
        if message in _RESET_COMMANDS:
            state["route"] = "reset"
        elif session_id in self._sessions:
            if self._looks_like_new_reservation_request(message):
                state["route"] = "restart_reservation"
            else:
                state["route"] = "continue_reservation"
        else:
            state["route"] = "classify"

        return state

    def _reset_session(self, state):
        self._sessions.pop(state["session_id"], None)
        state["response"] = (
            "The current reservation process has been cancelled. "
            "You can start a new reservation whenever you are ready.")
        return state

    def _restart_reservation(self, state):
        session_id = state["session_id"]
        self._sessions[session_id] = {}
        return self._collect_reservation(state, session_id=session_id)

    def _classify_intent(self, state):
        result = self.llm.invoke(
            [
                SystemMessage(content="You are an intent classifier."),
                HumanMessage(
                    content=_INTENT_PROMPT.format(message=state["message"]))])
        intent = result.content.strip().lower()
        state["intent"] = "reservation" if "reservation" in intent else "info"
        return state

    def _answer_info(self, state):
        state["response"] = self.rag_chain.answer(state["message"])
        return state

    def _collect_reservation_node(self, state):
        return self._collect_reservation(
            state,
            session_id=state["session_id"])

    def _collect_reservation(self, state, session_id="default"):
        slots = self._sessions.setdefault(session_id, {})
        self._extract_slots(state["message"], slots)

        missing = [slot for slot in _REQUIRED_SLOTS if slot not in slots]
        if missing:
            state["response"] = self._ask_for_missing(missing)
            state["slots"] = dict(slots)
            return state

        period_start = datetime.fromisoformat(slots["period_start"])
        period_end = datetime.fromisoformat(slots["period_end"])

        errors = self.validator.validate(
            name=slots["name"],
            surname=slots["surname"],
            car_number=slots["car_number"],
            period_start=period_start,
            period_end=period_end)
        if errors:
            for field in errors:
                slots.pop(field, None)

            state["slots"] = dict(slots)
            state["response"] = " ".join(errors.values())
            return state

        parking_space = self.db.find_available_space(
            period_start=period_start,
            period_end=period_end)
        if parking_space is None:
            slots.pop("period_start", None)
            slots.pop("period_end", None)
            state["slots"] = dict(slots)
            state["response"] = (
                "No parking space is available for the requested period. "
                "Please provide a different start and end date/time.")
            return state

        reservation_id = self.db.create_reservation(
            parking_space_id=parking_space["id"],
            name=slots["name"],
            surname=slots["surname"],
            car_number=slots["car_number"],
            period_start=period_start,
            period_end=period_end)

        state["reservation_id"] = reservation_id
        state["response"] = (
            f"Thanks {slots['name']}, your reservation request for Zone "
            f"{parking_space['zone']} has been submitted and is pending administrator "
            f"approval. Reservation reference: {reservation_id}")
        self._sessions.pop(session_id, None)
        return state

    def _extract_slots(self, message, slots):
        normalized = message.strip()
        dates = _DATE_RE.findall(normalized)

        if len(dates) >= 2:
            slots["period_start"] = dates[0].replace("T", " ")
            slots["period_end"] = dates[1].replace("T", " ")
        elif len(dates) == 1:
            value = dates[0].replace("T", " ")

            if "period_start" not in slots:
                slots["period_start"] = value
            elif "period_end" not in slots:
                slots["period_end"] = value

        car_match = _CAR_RE.search(normalized.upper())
        if car_match:
            slots["car_number"] = (
                car_match.group(1).replace(" ", "").replace("-", "")
            )

        full_name_match = re.search(
            r"\bmy\s+name\s+is\s+"
            r"([A-Za-zÀ-ÖØ-öø-ÿ'’-]+)\s+"
            r"([A-Za-zÀ-ÖØ-öø-ÿ'’-]+)\b",
            normalized,
            re.IGNORECASE)
        if full_name_match:
            slots["name"] = full_name_match.group(1).title()
            slots["surname"] = full_name_match.group(2).title()
        else:
            name_match = re.search(
                r"\bname[: ]+([A-Za-zÀ-ÖØ-öø-ÿ'’-]+)\b",
                normalized,
                re.IGNORECASE)
            if name_match and "name" not in slots:
                slots["name"] = name_match.group(1).title()

            surname_match = re.search(
                r"\bsurname[: ]+([A-Za-zÀ-ÖØ-öø-ÿ'’-]+)\b",
                normalized,
                re.IGNORECASE)
            if surname_match:
                slots["surname"] = surname_match.group(1).title()

        parts = [part.strip() for part in normalized.split(",")]
        if len(parts) >= 2:
            if "name" not in slots and _WORD_RE.fullmatch(parts[0]):
                slots["name"] = parts[0].title()
            if "surname" not in slots and _WORD_RE.fullmatch(parts[1]):
                slots["surname"] = parts[1].title()

        if _WORD_RE.fullmatch(normalized):
            if "name" not in slots:
                slots["name"] = normalized.title()
            elif "surname" not in slots:
                slots["surname"] = normalized.title()

    def _ask_for_missing(self, missing):
        prompts = {
            "name": "your first name",
            "surname": "your surname",
            "car_number": "your car registration number",
            "period_start": "the reservation start date/time (YYYY-MM-DD HH:MM)",
            "period_end": "the reservation end date/time (YYYY-MM-DD HH:MM)"}
        asks = ", ".join(prompts[slot] for slot in missing)
        return f"To complete your reservation I still need: {asks}."

    def _looks_like_new_reservation_request(self, message):
        phrases = (
            "i want to reserve",
            "i want to book",
            "book a parking",
            "reserve a parking",
            "new reservation",
            "start a new reservation")
        return any(phrase in message for phrase in phrases)

    def handle_message(self, message, session_id="default"):
        result = self.graph.invoke(
            {
                "message": message,
                "session_id": session_id})
        return result["response"]
