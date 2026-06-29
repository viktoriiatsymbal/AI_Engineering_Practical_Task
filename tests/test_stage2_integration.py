from datetime import datetime
from types import SimpleNamespace
from fastapi.testclient import TestClient
from src.admin_api import create_app
from src.database import Database, ParkingSpace

class DeterministicAdminAgent:
    def __init__(self, database):
        self.database = database
        self.pending = {}

    def propose(self, reservation_id, instruction, thread_id):
        action = (
            "refuse_reservation"
            if "refuse" in instruction.lower()
            else "approve_reservation")
        self.pending[thread_id] = (reservation_id, action)
        self.database.mark_review_awaiting_confirmation(
            thread_id, action)
        return {
            "status": "awaiting_confirmation",
            "thread_id": thread_id,
            "reservation_id": reservation_id,
            "action_requests": [
                {
                    "name": action,
                    "args": {"reservation_id": reservation_id}}],
            "review_configs": []}

    def resume(self, thread_id, decision, message=None):
        reservation_id, action = self.pending[thread_id]
        if decision == "approve":
            status = (
                "approved"
                if action == "approve_reservation"
                else "refused")
            self.database.resolve_admin_review(
                reservation_id, status, message)
        return {"status": "completed", "thread_id": thread_id}

def _setup(tmp_path):
    database_path = tmp_path / "stage2_integration.db"
    database = Database(
        dsn=f"sqlite:///{database_path}")
    database.create_all()
    with database.session() as session:
        space = ParkingSpace(
            zone="A",
            is_available=True,
            hourly_price=2.5)
        session.add(space)
        session.flush()
        space_id = space.id

    reservation_id = database.create_reservation(
        parking_space_id=space_id,
        name="Anna",
        surname="Smith",
        car_number="AA1234BB",
        period_start=datetime(2026, 7, 10, 10, 0),
        period_end=datetime(2026, 7, 10, 12, 0))
    settings = SimpleNamespace(admin_api_token="secret")
    agent = DeterministicAdminAgent(database)
    app = create_app(settings, database, agent)
    return database, reservation_id, app

def _headers():
    return {"Authorization": "Bearer secret"}

def _run_flow(instruction, tmp_path):
    database, reservation_id, app = _setup(tmp_path)
    with TestClient(app) as client:
        review = client.post(
            "/admin/requests",
            headers=_headers(),
            json={"reservation_id": reservation_id})
        assert review.status_code == 201
        thread_id = review.json()["thread_id"]

        proposed = client.post(
            "/admin/commands",
            headers=_headers(),
            json={
                "reservation_id": reservation_id,
                "instruction": instruction})
        assert proposed.status_code == 200
        assert (
            proposed.json()["status"]
            == "awaiting_confirmation")

        resumed = client.post(
            "/admin/decisions",
            headers=_headers(),
            json={
                "thread_id": thread_id,
                "decision": "approve",
                "message": None})
        assert resumed.status_code == 200

    return database, reservation_id

def test_stage2_approve_flow_end_to_end(tmp_path):
    database, reservation_id = _run_flow(
        "Approve this reservation",
        tmp_path)
    assert (
        database.get_reservation(reservation_id)["status"]
        == "approved")
    assert (
        database.get_admin_review(
            reservation_id
        )["review_state"]
        == "approved")

def test_stage2_refuse_flow_end_to_end(tmp_path):
    database, reservation_id = _run_flow(
        "Refuse this reservation",
        tmp_path)
    assert (
        database.get_reservation(reservation_id)["status"]
        == "refused")
    assert (
        database.get_admin_review(
            reservation_id
        )["review_state"]
        == "refused")
