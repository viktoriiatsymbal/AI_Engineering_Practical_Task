from datetime import datetime
from src.database import Database, ParkingSpace

def _db_with_reservation():
    db = Database(dsn="sqlite:///:memory:")
    db.create_all()

    with db.session() as session:
        space = ParkingSpace(
            zone="A",
            is_available=True,
            hourly_price=2.5)
        session.add(space)
        session.flush()
        space_id = space.id

    reservation_id = db.create_reservation(
        parking_space_id=space_id,
        name="Anna",
        surname="Smith",
        car_number="AA1234BB",
        period_start=datetime(2026, 7, 2, 10, 0),
        period_end=datetime(2026, 7, 2, 12, 0))
    return db, reservation_id

def test_create_admin_review_is_idempotent():
    db, reservation_id = _db_with_reservation()

    first = db.create_admin_review(
        reservation_id,
        "thread-1")
    second = db.create_admin_review(
        reservation_id,
        "thread-2")

    assert first["thread_id"] == "thread-1"
    assert second["thread_id"] == "thread-1"

def test_resolve_admin_review_updates_reservation():
    db, reservation_id = _db_with_reservation()
    db.create_admin_review(reservation_id, "thread-1")

    db.resolve_admin_review(
        reservation_id,
        "approved",
        "Looks good")

    assert db.get_reservation(reservation_id)["status"] == "approved"
    assert (
        db.get_admin_review(reservation_id)["review_state"]
        == "approved")
