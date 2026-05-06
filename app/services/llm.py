from __future__ import annotations

from typing import Any

from app.config import GROQ_API_KEY, LLM_MODEL, LLM_PROVIDER, LOCAL_LLM_PATH

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

    def generate(self, prompt: str, temperature=0.2, max_tokens=300) -> str:
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

        if self.provider == "local":
            if not self.local_model_path:
                return "⚠️ LOCAL_LLM_PATH is not configured."
            return (
                "⚠️ Local LLM is configured, but the current runtime does not support a local model backend. "
                "Install a compatible local inference library or configure a local model server."
            )

        return f"⚠️ Unsupported LLM provider '{self.provider}'."
