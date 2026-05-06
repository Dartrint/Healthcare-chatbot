from __future__ import annotations

from typing import Callable


class MCPGateway:
    """
    Lightweight MCP-compatible gateway.
    Handlers can be registered later for real MCP tool calls.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[str], str]] = {}

    def register(self, tool_name: str, handler: Callable[[str], str]) -> None:
        self._handlers[tool_name] = handler

    def query(self, tool_name: str, payload: str) -> str:
        handler = self._handlers.get(tool_name)
        if handler is None:
            return ""
        try:
            return handler(payload)
        except Exception:
            return ""
