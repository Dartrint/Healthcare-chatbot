#!/usr/bin/env python3
"""
LangSmith tracing setup for monitoring, debugging, and evaluation.
Wraps key services with @traceable decorators.

Usage:
    from app.services.tracer import trace_llm, trace_search, trace_graph

    @trace_llm
    def my_llm_call(prompt: str) -> str: ...
"""
from __future__ import annotations

import functools
import os
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

# Enable LangSmith only if LANGCHAIN_API_KEY is set
_ENABLED = bool(os.getenv("LANGCHAIN_API_KEY", ""))


def _get_tracer(run_type: str = "chain") -> Callable[[F], F]:
    """Return @traceable decorator or no-op depending on config."""
    if not _ENABLED:
        return lambda f: f  # no-op passthrough

    try:
        from langsmith import traceable as _traceable
        return _traceable(run_type=run_type)
    except ImportError:
        return lambda f: f


# Pre-built decorators for each service layer
trace_llm = _get_tracer("llm")       # LLM.generate()
trace_search = _get_tracer("tool")   # Tavily search, web_search
trace_graph = _get_tracer("chain")   # Graph node routing
trace_chain = _get_tracer("chain")   # General chain steps