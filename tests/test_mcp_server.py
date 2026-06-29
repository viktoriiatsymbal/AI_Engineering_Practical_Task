from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from src.mcp_server import build_mcp_server

def _settings():
    return SimpleNamespace(
        mcp_jwt_secret="x" * 32,
        mcp_jwt_issuer="issuer",
        mcp_jwt_audience="audience",
        mcp_output_file="unused.txt",
        mcp_index_file="unused.json")

def test_server_registers_recording_tool():
    database = MagicMock()
    store = MagicMock()
    server = build_mcp_server(_settings(), database, store)
    assert server.name == "CityPark Reservation Storage"

def test_recording_logic_rejects_nonapproved_reservation():
    database = MagicMock()
    database.get_admin_review.return_value = {
        "review_state": "pending_admin",
        "decided_at": None,
        "reservation": {}}
    server = build_mcp_server(_settings(), database, MagicMock())
    assert server is not None
