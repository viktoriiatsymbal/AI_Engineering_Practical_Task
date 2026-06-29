import json
from unittest.mock import MagicMock
from src.admin_tools import build_admin_tools

def test_approve_calls_mcp_after_database_approval():
    database = MagicMock()
    database.resolve_admin_review.return_value = {
        "reservation_id": "r1",
        "review_state": "approved"}
    recorder = MagicMock()
    recorder.record.return_value = {"status": "recorded"}
    tools = {t.name: t for t in build_admin_tools(database, recorder)}

    result = json.loads(
        tools["approve_reservation"].invoke({"reservation_id": "r1"}))

    recorder.record.assert_called_once_with("r1")
    assert result["mcp_recording"]["status"] == "recorded"


def test_refuse_never_calls_mcp():
    database = MagicMock()
    database.resolve_admin_review.return_value = {
        "reservation_id": "r1",
        "review_state": "refused"}
    recorder = MagicMock()
    tools = {t.name: t for t in build_admin_tools(database, recorder)}

    tools["refuse_reservation"].invoke({"reservation_id": "r1"})

    recorder.record.assert_not_called()
