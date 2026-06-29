from datetime import datetime, time
from unittest.mock import MagicMock, patch
from src.chatbot import ParkingChatbot
from src.config import load_settings
from src.database import Database, ParkingSpace, WorkingHours
from src.guardrails import GuardRails

def make_bot():
    settings = load_settings()
    db = Database(dsn="sqlite:///:memory:")
    db.create_all()

    with db.session() as session:
        session.add(
            ParkingSpace(
                zone="A",
                is_available=True,
                hourly_price=2.5))
        session.add(
            WorkingHours(
                day_of_week="Wednesday",
                open_time=time(7, 0),
                close_time=time(23, 0)))

    fake_rag = MagicMock()
    fake_guardrails = MagicMock(spec=GuardRails)
    with patch("src.chatbot.ChatOpenAI"):
        bot = ParkingChatbot(settings, fake_rag, db, fake_guardrails)
    bot.validator.now_provider = lambda: datetime(2026, 6, 30, 8, 0)
    return bot, db

def test_extract_slots_parses_car_number_and_dates():
    bot, _ = make_bot()
    slots = {}
    bot._extract_slots(
        "name: Anna surname: Ponomarenko car AB1234CD "
        "from 2026-07-01 10:00 to 2026-07-01 12:00",
        slots)

    assert slots["name"] == "Anna"
    assert slots["surname"] == "Ponomarenko"
    assert slots["car_number"] == "AB1234CD"
    assert slots["period_start"] == "2026-07-01 10:00"
    assert slots["period_end"] == "2026-07-01 12:00"

def test_ask_for_missing_lists_unfilled_slots():
    bot, _ = make_bot()
    message = bot._ask_for_missing(["name", "car_number"])

    assert "first name" in message
    assert "car registration number" in message

def test_collect_reservation_creates_db_row_once_complete():
    bot, db = make_bot()
    state = {
        "message": (
            "name: Jane surname: Smith car XY9876ZZ "
            "from 2026-07-01 10:00 to 2026-07-01 12:00")}
    result = bot._collect_reservation(
        state,
        session_id="test-session")

    assert "reservation_id" in result
    reservation = db.get_reservation(result["reservation_id"])
    assert reservation["name"] == "Jane"
    assert reservation["parking_space_id"] is not None
    assert reservation["status"] == "pending"

def test_collect_reservation_asks_for_missing_info_when_incomplete():
    bot, _ = make_bot()
    state = {"message": "name: Jane"}
    result = bot._collect_reservation(
        state,
        session_id="test-session-2")

    assert "reservation_id" not in result
    assert "surname" in result["response"]

def test_collect_reservation_rejects_short_names():
    bot, _ = make_bot()
    state = {
        "message": (
            "V, T, AA1234BB, "
            "2026-07-01 10:00, 2026-07-01 12:00")}
    result = bot._collect_reservation(
        state,
        session_id="short-name-session")

    assert "reservation_id" not in result
    assert "at least 2 letters" in result["response"]

def test_collect_reservation_reports_no_available_space():
    bot, _ = make_bot()
    first = {
        "message": (
            "name: Jane surname: Smith car XY9876ZZ "
            "from 2026-07-01 10:00 to 2026-07-01 12:00")}
    bot._collect_reservation(first, session_id="first-session")
    second = {
        "message": (
            "name: Anna surname: Ponomarenko car AA1234BB "
            "from 2026-07-01 11:00 to 2026-07-01 13:00")}
    result = bot._collect_reservation(
        second,
        session_id="second-session")

    assert "reservation_id" not in result
    assert "No parking space is available" in result["response"]

def test_handle_message_invokes_compiled_graph():
    bot, _ = make_bot()
    original_invoke = bot.graph.invoke
    bot.graph.invoke = MagicMock(wraps=original_invoke)
    bot.llm.invoke.return_value.content = "reservation"
    response = bot.handle_message(
        "I want to reserve a parking space.",
        session_id="graph-session")
    bot.graph.invoke.assert_called_once_with(
        {
            "message": "I want to reserve a parking space.",
            "session_id": "graph-session"})
    assert "first name" in response

def test_graph_preserves_session_id_across_messages():
    bot, _ = make_bot()
    bot.llm.invoke.return_value.content = "reservation"
    first_response = bot.handle_message(
        "I want to reserve a parking space.",
        session_id="customer-42")
    second_response = bot.handle_message(
        "Anna",
        session_id="customer-42")

    assert "first name" in first_response
    assert "surname" in second_response
    assert bot._sessions["customer-42"]["name"] == "Anna"

def test_graph_routes_information_request_to_rag():
    bot, _ = make_bot()
    bot.llm.invoke.return_value.content = "info"
    bot.rag_chain.answer.return_value = "CityPark is downtown."
    response = bot.handle_message(
        "Where are you located?",
        session_id="info-session")

    assert response == "CityPark is downtown."
    bot.rag_chain.answer.assert_called_once_with("Where are you located?")

def test_graph_reset_command_clears_active_session():
    bot, _ = make_bot()
    bot._sessions["reset-session"] = {
        "name": "Anna",
        "surname": "Smith"}
    response = bot.handle_message(
        "cancel",
        session_id="reset-session")

    assert "cancelled" in response
    assert "reset-session" not in bot._sessions

def test_new_reservation_request_resets_existing_session_through_graph():
    bot, _ = make_bot()
    bot._sessions["test-session"] = {
        "name": "Anna",
        "surname": "Smith",
        "car_number": "AA1234BB"}
    response = bot.handle_message(
        "I want to book",
        session_id="test-session")

    assert "first name" in response
    assert bot._sessions["test-session"] == {}

def test_extract_slots_fills_start_and_end_across_separate_messages():
    bot, _ = make_bot()
    slots = {}
    bot._extract_slots("2026-07-01 10:00", slots)
    assert slots["period_start"] == "2026-07-01 10:00"
    assert "period_end" not in slots
    bot._extract_slots("2026-07-01 12:00", slots)
    assert slots["period_end"] == "2026-07-01 12:00"

def test_graph_collects_dates_across_separate_messages():
    bot, db = make_bot()
    bot.llm.invoke.return_value.content = "reservation"
    session_id = "separate-dates-session"

    bot.handle_message("I want to book", session_id=session_id)
    bot.handle_message("Anna", session_id=session_id)
    bot.handle_message("Ponomarenko", session_id=session_id)
    bot.handle_message("AA1234BB", session_id=session_id)
    bot.handle_message("2026-07-01 10:00", session_id=session_id)
    response = bot.handle_message(
        "2026-07-01 12:00",
        session_id=session_id)

    assert "pending administrator approval" in response
    assert session_id not in bot._sessions
