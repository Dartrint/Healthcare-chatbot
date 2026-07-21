from __future__ import annotations

import datetime
import os
import random
from typing import Callable

from app.services.tracer import trace_search


class MCPGateway:
    """
    MCP-compatible gateway with built-in tool handlers and extensibility.
    New handlers can be registered for real MCP tool calls.
    Uses Tavily for web search when API key is configured.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[str], str]] = {}
        self._register_defaults()
        self._tavily_client = self._init_tavily()

    def _init_tavily(self) -> object | None:
        """Initialize Tavily client if API key available."""
        api_key = os.getenv("TAVILY_API_KEY", "")
        if not api_key:
            return None
        try:
            from tavily import TavilyClient
            return TavilyClient(api_key=api_key)
        except ImportError:
            return None

    def _register_defaults(self) -> None:
        """Register built-in lightweight handlers."""
        self._handlers["weather"] = self._handle_weather
        self._handlers["general_knowledge"] = self._handle_general_knowledge
        self._handlers["time_date"] = self._handle_time_date
        self._handlers["medical_knowledge"] = self._handle_medical_knowledge
        self._handlers["web_search"] = self._handle_web_search

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

    # ── Built-in Handlers ──────────────────────────────────────────────

    def _handle_weather(self, query: str) -> str:
        """Simulate weather data. In production, call weather API."""
        today = datetime.date.today()
        temp = round(random.uniform(18, 38), 1)
        conditions = ["nắng", "có mây", "mưa nhẹ", "nhiều mây", "trong xanh"]
        cond = random.choice(conditions)
        humidity = random.randint(50, 95)
        return (
            f"Hôm nay ({today.strftime('%d/%m/%Y')}): {cond}, "
            f"{temp}°C, độ ẩm {humidity}%"
        )

    def _handle_general_knowledge(self, query: str) -> str:
        """Placeholder for general knowledge retrieval. Add wiki/DB lookup later."""
        return ""

    def _handle_time_date(self, query: str) -> str:
        """Return current date and time."""
        now = datetime.datetime.now()
        return (
            f"Bây giờ là {now.strftime('%H:%M:%S')}, ngày "
            f"{now.strftime('%d/%m/%Y')}"
        )

    def _handle_medical_knowledge(self, query: str) -> str:
        """Placeholder for medical knowledge from external APIs. Add PubMed/WHO later."""
        return ""

    @trace_search
    def _handle_web_search(self, query: str) -> str:
        """Search web via Tavily for real-time information."""
        if not self._tavily_client:
            return ""
        try:
            response = self._tavily_client.search(
                query=query,
                max_results=5,
                search_depth="advanced",
                include_answer=True,
            )
            answer = response.get("answer", "")
            results = response.get("results", [])
            if not answer and not results:
                return ""
            lines = []
            if answer:
                lines.append(f"📝 {answer}")
            for i, r in enumerate(results[:3], 1):
                title = r.get("title", "")
                snippet = r.get("content", "")[:150]
                if title:
                    lines.append(f"{i}. {title}: {snippet}")
            return "\n".join(lines)
        except Exception:
            return ""
