from datetime import datetime
from src.approved_reservation_store import ApprovedReservationStore

def _reservation():
    return {
        "name": "Anna",
        "surname": "Smith",
        "car_number": "AA1234BB",
        "period_start": datetime(2026, 7, 3, 10, 0),
        "period_end": datetime(2026, 7, 3, 12, 0)}

def test_store_writes_required_format(tmp_path):
    store = ApprovedReservationStore(
        tmp_path / "approved.txt",
        tmp_path / "index.json")
    result = store.record(
        "r1", _reservation(), datetime(2026, 7, 1, 8, 0))
    assert result["status"] == "recorded"
    assert (tmp_path / "approved.txt").read_text().strip() == (
        "Anna Smith | AA1234BB | "
        "2026-07-03T10:00:00 to 2026-07-03T12:00:00 | "
        "2026-07-01T08:00:00")

def test_store_is_idempotent(tmp_path):
    store = ApprovedReservationStore(
        tmp_path / "approved.txt",
        tmp_path / "index.json")
    first = store.record("r1", _reservation(), datetime(2026, 7, 1, 8, 0))
    second = store.record("r1", _reservation(), datetime(2026, 7, 1, 8, 0))
    assert first["status"] == "recorded"
    assert second["status"] == "already_recorded"
    assert len((tmp_path / "approved.txt").read_text().splitlines()) == 1
