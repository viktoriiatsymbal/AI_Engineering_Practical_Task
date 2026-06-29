import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from src.mcp_client import MCPReservationRecorder

def _settings():
    return SimpleNamespace(
        mcp_server_url="http://localhost:8001/mcp",
        mcp_access_token="token",
        mcp_timeout_seconds=2,
        mcp_retry_attempts=1)

def test_client_invokes_named_mcp_tool():
    tool = MagicMock()
    tool.name = "record_approved_reservation"
    tool.ainvoke = AsyncMock(return_value={"status": "recorded"})
    client = MagicMock()
    client.get_tools = AsyncMock(return_value=[tool])
    factory = MagicMock(return_value=client)

    result = asyncio.run(
        MCPReservationRecorder(_settings(), factory).arecord("r1"))

    assert result == {"status": "recorded"}
    tool.ainvoke.assert_awaited_once_with({"reservation_id": "r1"})

def test_client_fails_when_tool_is_missing():
    client = MagicMock()
    client.get_tools = AsyncMock(return_value=[])
    factory = MagicMock(return_value=client)

    try:
        asyncio.run(MCPReservationRecorder(_settings(), factory).arecord("r1"))
    except RuntimeError as exc:
        assert "MCP tool not found" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
