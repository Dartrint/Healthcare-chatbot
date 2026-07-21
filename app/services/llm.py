from __future__ import annotations

import json
from typing import Any

import requests
from app.config import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    GROQ_API_KEY,
    LLM_MODEL,
    LLM_PROVIDER,
    LOCAL_LLM_PATH,
    OLLAMA_BASE_URL,
    OLLAMA_TIMEOUT,
)
from app.services.tracer import trace_llm

try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None


class LLMService:
    def __init__(self) -> None:
        self.provider = LLM_PROVIDER
        self.model = LLM_MODEL
        self.local_model_path = LOCAL_LLM_PATH
        self.client = None

        if self.provider == "groq":
            if Groq is None:
                raise RuntimeError("groq package is required for GROQ provider")
            self.client = Groq(api_key=GROQ_API_KEY)

        if self.provider == "ollama":
            self.ollama_url = OLLAMA_BASE_URL.rstrip("/")
            self.timeout = OLLAMA_TIMEOUT

    @trace_llm
    def generate(self, prompt: str, temperature=DEFAULT_TEMPERATURE, max_tokens=DEFAULT_MAX_TOKENS) -> str:
        if self.provider == "groq" and self.client is not None:
            try:
                res = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return res.choices[0].message.content.strip()
            except Exception:
                return "⚠️ LLM error: Groq request failed."

        if self.provider == "ollama":
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                }
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "").strip()
            except requests.exceptions.ConnectionError:
                return (
                    "⚠️ Không thể kết nối Ollama. Hãy đảm bảo Ollama đang chạy:\n"
                    "1. Cài Ollama: https://ollama.com/download\n"
                    "2. Chạy: ollama serve\n"
                    "3. Tải model: ollama pull llama3.2"
                )
            except Exception as e:
                return f"⚠️ LLM error: {str(e)}"

        if self.provider == "local":
            if not self.local_model_path:
                return "⚠️ LOCAL_LLM_PATH is not configured."
            return (
                "⚠️ Local LLM is configured, but the current runtime does not support a local model backend. "
                "Install a compatible local inference library or configure a local model server."
            )

        return f"⚠️ Unsupported LLM provider '{self.provider}'."