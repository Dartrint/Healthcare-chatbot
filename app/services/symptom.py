from __future__ import annotations

from app.services.llm import LLMService


class SymptomService:
    def __init__(self, llm: LLMService):
        self.llm = llm

    def analyze(self, user_input: str, context: str = "") -> str:
        prompt = f"""
You are a healthcare triage assistant.

Patient: {user_input}

Give:
- possible causes
- severity
- what to do

Keep it simple and safe.
"""

        return self.llm.generate(prompt, max_tokens=300)