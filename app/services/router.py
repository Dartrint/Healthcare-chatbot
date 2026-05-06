from __future__ import annotations

import json
import re
import unicodedata
from typing import Dict
from langchain_core.prompts import PromptTemplate

from app.services.llm import LLMService


PROMPT = PromptTemplate(
    input_variables=["q", "context", "recent_intent"],
    template="""
You are an intent router for a healthcare assistant.

Available intents:
- RAG: explain medical knowledge, definitions, causes, prevention.
- SYMPTOM: user reports personal symptoms or asks triage for current condition.
- PLANNER: create/update/list reminders, schedule, tasks, medication plan.
- CHAT: casual talk or unclear request.

Recent intent: {recent_intent}
Recent context:
{context}

Q: {q}

Return JSON:
{{"intent": "RAG|SYMPTOM|PLANNER|CHAT", "confidence": 0.0}}
"""
)


class RouterService:
    def __init__(self, llm: LLMService):
        self.llm = llm
        self._intent_keywords = {
            "PLANNER": [
                "plan", "lịch", "nhắc", "reminder", "task", "todo", "việc cần làm",
                "uống thuốc", "appointment", "hẹn", "theo dõi",
                "lich", "nhac", "viec can lam", "uong thuoc", "hen", "theo doi",
            ],
            "RAG": [
                "là gì", "what is", "how", "tại sao", "nguyên nhân", "giải thích",
                "triệu chứng của", "phòng ngừa", "dinh dưỡng", "thuốc",
                "la gi", "tai sao", "nguyen nhan", "giai thich", "trieu chung cua", "phong ngua", "dinh duong", "thuoc",
            ],
            "SYMPTOM": [
                "đau", "sốt", "ho", "mệt", "chóng mặt", "khó thở", "buồn nôn",
                "fever", "pain", "cough", "headache", "symptom",
                "dau", "sot", "met", "chong mat", "kho tho", "buon non",
            ],
        }

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text.lower())
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        return re.sub(r"\s+", " ", ascii_text).strip()

    def _rule_classify(self, question: str) -> Dict[str, object]:
        q = question.lower().strip()
        q_ascii = self._normalize_text(question)
        if not q:
            return {"intent": "CHAT", "confidence": 0.2, "reason": "empty_input"}

        scores = {intent: 0 for intent in self._intent_keywords}
        for intent, keywords in self._intent_keywords.items():
            for keyword in keywords:
                if keyword in q or keyword in q_ascii:
                    scores[intent] += 1

        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        if best_score == 0:
            return {"intent": "CHAT", "confidence": 0.45, "reason": "no_keyword_match"}

        # avoid over-routing to symptom unless multiple strong symptom tokens
        if best_intent == "SYMPTOM" and best_score == 1 and len(q.split()) > 6:
            return {"intent": "CHAT", "confidence": 0.55, "reason": "weak_symptom_signal"}

        confidence = min(0.95, 0.55 + 0.1 * best_score)
        return {"intent": best_intent, "confidence": confidence, "reason": "rule_match"}

    @staticmethod
    def _extract_json(raw: str) -> Dict[str, object] | None:
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except Exception:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except Exception:
                return None

    def classify(self, question: str, context: str = "", recent_intent: str = "") -> Dict:
        q = question.lower().strip()
        q_ascii = self._normalize_text(question)
        if recent_intent in {"RAG", "SYMPTOM", "PLANNER", "CHAT"}:
            follow_up_tokens = ["còn", "vậy", "thế", "tiếp", "nó", "điều đó", "what about", "how about", "and then"]
            follow_up_tokens_ascii = ["con", "vay", "the", "tiep", "no", "dieu do"]
            if len(q.split()) <= 8 and (
                any(token in q for token in follow_up_tokens)
                or any(token in q_ascii for token in follow_up_tokens_ascii)
            ):
                return {"intent": recent_intent, "confidence": 0.78, "reason": "follow_up_context"}

        planner_override = [
            "kế hoạch", "plan", "reminder", "nhắc", "task", "todo", "lịch",
            "uống thuốc lúc", "schedule", "hẹn lịch",
            "ke hoach", "nhac", "lich", "uong thuoc luc", "hen lich",
        ]
        if any(token in q for token in planner_override) or any(token in q_ascii for token in planner_override):
            return {"intent": "PLANNER", "confidence": 0.88, "reason": "planner_override"}

        rule_result = self._rule_classify(question)
        if rule_result["confidence"] >= 0.7:
            return rule_result

        prompt = PROMPT.format(
            q=question,
            context=context or "No previous context.",
            recent_intent=recent_intent or "UNKNOWN",
        )
        raw = self.llm.generate(prompt, temperature=0)
        data = self._extract_json(raw)
        if not data:
            return rule_result

        intent = str(data.get("intent", "CHAT")).upper()
        confidence = float(data.get("confidence", 0.0))
        if intent not in {"RAG", "SYMPTOM", "PLANNER", "CHAT"}:
            return rule_result

        # prefer non-symptom for weak confidence to reduce false positives
        if intent == "SYMPTOM" and confidence < 0.75:
            return rule_result

        return {
            "intent": intent,
            "confidence": max(confidence, float(rule_result["confidence"])),
            "reason": "llm_refined",
        }