import json
from unittest.mock import MagicMock
from src.admin_tools import build_admin_tools

def test_approve_tool_updates_database():
    database = MagicMock()
    database.resolve_admin_review.return_value = {
        "reservation_id": "r1",
        "review_state": "approved"}
    tools = {tool.name: tool for tool in build_admin_tools(database)}

    result = tools["approve_reservation"].invoke(
        {"reservation_id": "r1", "comment": "OK"})

    database.resolve_admin_review.assert_called_once_with(
        reservation_id="r1",
        decision="approved",
        comment="OK")
    assert json.loads(result)["review_state"] == "approved"

def test_refuse_tool_updates_database():
    database = MagicMock()
    database.resolve_admin_review.return_value = {
        "reservation_id": "r1",
        "review_state": "refused"}
    tools = {tool.name: tool for tool in build_admin_tools(database)}

    tools["refuse_reservation"].invoke(
        {"reservation_id": "r1", "comment": "Full"})

    database.resolve_admin_review.assert_called_once_with(
        reservation_id="r1",
        decision="refused",
        comment="Full")
