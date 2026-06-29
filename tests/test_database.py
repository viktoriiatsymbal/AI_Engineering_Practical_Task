from datetime import datetime, time
from src.database import Database, ParkingSpace, WorkingHours

def make_db():
    db = Database(dsn="sqlite:///:memory:")
    db.create_all()
    return db

def seed_space_and_hours(db):
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

def test_get_available_spaces_filters_unavailable():
    db = make_db()
    with db.session() as session:
        session.add(ParkingSpace(zone="A", is_available=True, hourly_price=2.5))
        session.add(ParkingSpace(zone="C", is_available=False, hourly_price=2.0))
    available = db.get_available_spaces()

    assert {space["zone"] for space in available} == {"A"}

def test_find_available_space_ignores_conflicting_space():
    db = make_db()
    with db.session() as session:
        first = ParkingSpace(zone="A", is_available=True, hourly_price=2.5)
        second = ParkingSpace(zone="B", is_available=True, hourly_price=3.0)
        session.add_all([first, second])
        session.flush()
        first_id = first.id
        second_id = second.id
    db.create_reservation(
        parking_space_id=first_id,
        name="John",
        surname="Doe",
        car_number="AA1234BB",
        period_start=datetime(2026, 7, 1, 10, 0),
        period_end=datetime(2026, 7, 1, 12, 0))
    available = db.find_available_space(
        datetime(2026, 7, 1, 11, 0),
        datetime(2026, 7, 1, 13, 0))

    assert available["id"] == second_id

def test_find_available_space_returns_none_when_all_conflict():
    db = make_db()
    with db.session() as session:
        space = ParkingSpace(zone="A", is_available=True, hourly_price=2.5)
        session.add(space)
        session.flush()
        space_id = space.id
    db.create_reservation(
        parking_space_id=space_id,
        name="John",
        surname="Doe",
        car_number="AA1234BB",
        period_start=datetime(2026, 7, 1, 10, 0),
        period_end=datetime(2026, 7, 1, 12, 0))

    assert db.find_available_space(
        datetime(2026, 7, 1, 11, 0),
        datetime(2026, 7, 1, 13, 0)) is None

def test_create_and_get_reservation_round_trip():
    db = make_db()
    with db.session() as session:
        space = ParkingSpace(zone="A", is_available=True, hourly_price=2.5)
        session.add(space)
        session.flush()
        space_id = space.id
    reservation_id = db.create_reservation(
        parking_space_id=space_id,
        name="John",
        surname="Doe",
        car_number="AB1234CD",
        period_start=datetime(2026, 7, 1, 10, 0),
        period_end=datetime(2026, 7, 1, 12, 0))
    reservation = db.get_reservation(reservation_id)

    assert reservation["parking_space_id"] == space_id
    assert reservation["name"] == "John"
    assert reservation["status"] == "pending"

def test_update_reservation_status():
    db = make_db()
    with db.session() as session:
        space = ParkingSpace(zone="A", is_available=True, hourly_price=2.5)
        session.add(space)
        session.flush()
        space_id = space.id
    reservation_id = db.create_reservation(
        parking_space_id=space_id,
        name="Jane",
        surname="Smith",
        car_number="XY9876ZZ",
        period_start=datetime(2026, 7, 1, 10, 0),
        period_end=datetime(2026, 7, 1, 12, 0))
    db.update_reservation_status(reservation_id, "approved")

    assert db.get_reservation(reservation_id)["status"] == "approved"
