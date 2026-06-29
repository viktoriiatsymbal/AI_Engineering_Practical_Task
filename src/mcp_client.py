"""
LangChain MCP adapter client used by the Stage 2 administrator tool
"""
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

class MCPReservationRecorder:
    """Invoke the real remote MCP tool through LangChain MCP adapters."""

    TOOL_NAME = "record_approved_reservation"

    def __init__(self, settings, client_factory=MultiServerMCPClient):
        self.settings = settings
        self.client_factory = client_factory
        if not settings.mcp_access_token:
            raise RuntimeError(
                "MCP_ACCESS_TOKEN is required for the Stage 3 MCP client")

    def _client(self):
        return self.client_factory(
            {
                "reservation_storage": {
                    "transport": "http",
                    "url": self.settings.mcp_server_url,
                    "headers": {
                        "Authorization": (
                            f"Bearer {self.settings.mcp_access_token}")}}})

    async def arecord(self, reservation_id):
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.settings.mcp_retry_attempts),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
            retry=retry_if_exception_type(Exception),
            reraise=True):
            with attempt:
                client = self._client()
                tools = await asyncio.wait_for(
                    client.get_tools(),
                    timeout=self.settings.mcp_timeout_seconds)
                tool = next(
                    (tool for tool in tools if tool.name == self.TOOL_NAME),
                    None)
                if tool is None:
                    raise RuntimeError(
                        f"MCP tool not found: {self.TOOL_NAME}")
                result = await asyncio.wait_for(
                    tool.ainvoke({"reservation_id": reservation_id}),
                    timeout=self.settings.mcp_timeout_seconds)

                if getattr(result, "status", None) == "error":
                    raise RuntimeError(str(getattr(result, "content", result)))
                return result

    def record(self, reservation_id: str):
        """Synchronous bridge for the existing synchronous LangChain tool."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arecord(reservation_id))
        raise RuntimeError(
            "record() cannot run inside an active event loop; use arecord()")
