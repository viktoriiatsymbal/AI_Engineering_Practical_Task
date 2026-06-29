from datetime import datetime, time
from email import errors
from src.database import Database, WorkingHours
from src.reservation_validator import ReservationValidator

def make_validator(now=datetime(2026, 6, 30, 8, 0)):
    db = Database(dsn="sqlite:///:memory:")
    db.create_all()
    with db.session() as session:
        session.add(
            WorkingHours(
                day_of_week="Thursday",
                open_time=time(7, 0),
                close_time=time(23, 0)))
    return ReservationValidator(
        db,
        max_duration_hours=8,
        now_provider=lambda: now)

def test_rejects_short_name_and_surname():
    validator = make_validator()
    errors = validator.validate(
        name="V",
        surname="T",
        car_number="AA1234BB",
        period_start=datetime(2026, 7, 2, 10, 0),
        period_end=datetime(2026, 7, 2, 12, 0))

    assert "name" in errors
    assert "surname" in errors

def test_rejects_invalid_car_number():
    validator = make_validator()
    errors = validator.validate(
        name="Anna",
        surname="Smith",
        car_number="invalid",
        period_start=datetime(2026, 7, 2, 10, 0),
        period_end=datetime(2026, 7, 2, 12, 0))

    assert "car_number" in errors

def test_rejects_past_reservation():
    validator = make_validator()
    errors = validator.validate(
        name="Anna",
        surname="Smith",
        car_number="AA1234BB",
        period_start=datetime(2026, 6, 29, 10, 0),
        period_end=datetime(2026, 6, 29, 12, 0))

    assert "period_start" in errors

def test_rejects_end_before_start():
    validator = make_validator()
    errors = validator.validate(
        name="Anna",
        surname="Smith",
        car_number="AA1234BB",
        period_start=datetime(2026, 7, 2, 12, 0),
        period_end=datetime(2026, 7, 2, 10, 0))

    assert "period_end" in errors

def test_rejects_too_long_reservation():
    validator = make_validator()
    errors = validator.validate(
        name="Anna",
        surname="Smith",
        car_number="AA1234BB",
        period_start=datetime(2026, 7, 2, 10, 0),
        period_end=datetime(2026, 7, 2, 20, 0))

    assert "period_end" in errors

def test_rejects_period_outside_working_hours():
    validator = make_validator()
    errors = validator.validate(
        name="Anna",
        surname="Smith",
        car_number="AA1234BB",
        period_start=datetime(2026, 7, 2, 5, 0),
        period_end=datetime(2026, 7, 2, 6, 0))

    assert "period_start" in errors

def test_accepts_valid_reservation():
    validator = make_validator()
    errors = validator.validate(
        name="Anna",
        surname="Smith",
        car_number="AA1234BB",
        period_start=datetime(2026, 7, 2, 10, 0),
        period_end=datetime(2026, 7, 2, 13, 0))

    assert errors == {}
