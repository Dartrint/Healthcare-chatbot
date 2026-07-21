from __future__ import annotations

import json
import re
from typing import Dict
from langchain_core.prompts import PromptTemplate

from app.services.llm import LLMService


# ── LLM PROMPT (Primary classifier) ─────────────────────────────────────

PROMPT = PromptTemplate(
    input_variables=["q", "context"],
    template="""You are an intent classifier for a healthcare AI assistant in Vietnamese language.

Classify the user's message into exactly ONE of these intents:

1. **RAG** — Medical knowledge questions: disease definitions, medication info, treatment, prevention, "là gì", "tác dụng", "cách chữa", "bệnh", medical terminology, health conditions, diagnosis info.
   Examples: "Bệnh tiểu đường là gì", "Thuốc panadol có tác dụng gì", "Cách phòng tránh ung thư"

2. **SYMPTOM** — User reports personal symptoms or asks about their own health condition. First-person narrative about how they feel. Describes specific body sensations, pain, discomfort THEY are experiencing.
   Examples: "Tôi bị sốt và đau đầu", "Em đau bụng quá", "Mình bị ho nhiều", "I have a headache"

3. **PLANNER** — Managing tasks, reminders, schedule, appointments, medication reminders. Creating/viewing plans. Keywords: thêm, việc, tạo, nhắc, lịch, kế hoạch, task, todo, công việc, uống thuốc.
   Examples: "Nhắc tôi uống thuốc lúc 8h", "Tạo task mới", "Xem lịch của tôi", "Thêm việc uống thuốc ngày mai", "Tôi có việc cần làm"
   IMPORTANT: Delete/complete operations are handled via UI buttons, not chat. If user asks to delete/complete, redirect to buttons.

4. **CHAT** — Non-medical conversation: greetings, weather, general knowledge, small talk, thanks, farewell, entertainment, sports, technology, food (non-medical), daily life, about the assistant itself, weather queries, time/date.
   Examples: "Chào bạn", "Thời tiết hôm nay thế nào", "Bạn là ai", "Cảm ơn", "Hello", "What's the weather like"

Context from conversation history:
{context}

Q: {q}

Respond with ONLY a valid JSON object with NO other text:
{{"intent": "RAG|SYMPTOM|PLANNER|CHAT", "confidence": 0.0-1.0}}
""",
)


# ── MEDICAL KEYWORDS (fallback only) ────────────────────────────────────

RAG_PATTERNS = [
    r"(là gì|la gi|what is|what are|định nghĩa|dinh nghia|khái niệm|khai niem|thế nào|the nao)",
    r"(bệnh\s+\w+|benh\s+\w+|hội chứng|hoi chung|chứng bệnh|chung benh|triệu chứng|trieu chung|dấu hiệu|dau hieu|căn bệnh|can benh)",
    r"(thuốc|thuoc|medication|drug|liều lượng|lieu luong|cách dùng|cach dung|chỉ định|chi dinh|chống chỉ định|chong chi dinh|tương tác|tuong tac|tác dụng phụ|tac dung phu)",
    r"(điều trị|dieu tri|chữa|chua|trị|tri|phẫu thuật|phau thuat|hóa trị|hoa tri|xạ trị|xa tri)",
    r"(phòng ngừa|phong ngua|phòng tránh|phong tranh|dự phòng|du phong|ngăn ngừa|ngan ngua)",
    r"(nguyên nhân|nguyen nhan|cơ chế|co che|căn nguyên|can nguyen|tác nhân|tac nhan)",
    r"(chẩn đoán|chan doan|xét nghiệm|xet nghiem|siêu âm|sieu am|x-quang|mri|ct scan|nội soi|noi soi)",
    r"(dinh dưỡng|dinh duong|thực phẩm|thuc pham|chế độ ăn|che do an|kiêng|kieng)",
    r"(ung thư|ung thu|u bướu|u buou|viêm|viem|nhiễm trùng|nhiem trung|cao huyết áp|cao huyet ap|tiểu đường|tieu duong|đột quỵ|dot quy)",
    r"(cách phòng|cach phong|cách điều|cach dieu|cách chữa|cach chua|phương pháp|phuong phap)",
    r"(cancer|diabetes|hypertension|infection|inflammation|surgery|therapy|diagnosis|symptom|treatment|medication|disease|disorder|syndrome)",
]

SYMPTOM_PATTERNS = [
    r"(tôi|em|cháu|mình|con|tui|toi)\s+(bị|bi|có|co|thấy|thay|cảm thấy|cam thay)\s+(đau|dau|sốt|sot|ho|mệt|met|nôn|non|ói|oi|chóng mặt|chong mat)",
    r"(tôi|em|cháu|mình|con|tui)\s+(bị|bi|đau|dau|ho|mệt|met|sốt|sot)",
    r"(đau\s+đầu|dau\s+dau|đau\s+bụng|dau\s+bung|đau\s+lưng|dau\s+lung|đau\s+họng|dau\s+hong|đau\s+ngực|dau\s+nguc|đau\s+răng|dau\s+rang|đau\s+mắt|dau\s+mat|đau\s+khớp|dau\s+khop)",
    r"(sốt|sot)\s+(cao|nhẹ|nhe|vừa|vua|li bì|li bi|rét|ret)",
    r"(chóng\s+mặt|chong\s+mat|hoa\s+mắt|hoa\s+mat|ù\s+tai|u\s+tai|buồn\s+nôn|buon\s+non|khó\s+thở|kho\s+tho|khó\s+chịu|kho\s+chiu|mệt\s+mỏi|met\s+moi)",
    r"(mất\s+ngủ|mat\s+ngu|khó\s+ngủ|kho\s+ngu|chán\s+ăn|chan\s+an|mệt\s+quá|met\s+qua|đau\s+quá|dau\s+qua)",
    r"(nôn|non|ói|oi|ợ\s+chua|o\s+chua|trào\s+ngược|trao\s+nguoc)",
    r"(tiêu\s+chảy|tieu\s+chay|ỉa\s+chảy|ia\s+chay|táo\s+bón|tao\s+bon|đi\s+ngoài|di\s+ngoai)",
    r"(phát\s+ban|phat\s+ban|mẩn\s+ngứa|man\s+ngua|nổi\s+mề\s+đay|noi\s+me\s+day|dị\s+ứng|di\s+ung)",
    r"(sưng|sung|phù|phu|tấy|tay|đỏ|do|nóng|nong)",
    r"(ho\s+ra\s+đờm|ho\s+ra\s+dom|ho\s+ra\s+máu|ho\s+ra\s+mau|khạc\s+ra\s+đờm|khac\s+ra\s+dom)",
    r"(tê\s+bì|te\s+bi|tê\s+chân|te\s+chan|tê\s+tay|te\s+tay|yếu\s+liệt|yeu\s+liet)",
    r"(chảy\s+máu|chay\s+mau|xuất\s+huyết|xuat\s+huyet|bầm\s+tím|bam\s+tim|tím\s+tái|tim\s+tai)",
    r"(my\s+\w+\s+ hurts|i\s+(have|feel|am feeling)\s+(a\s+)?(headache|fever|cough|cold|pain|nausea|dizziness|sore)|i'm\s+(sick|not\s+feeling|feeling\s+unwell|in\s+pain))",
]


class RouterService:
    INTENTS = ["RAG", "SYMPTOM", "PLANNER", "CHAT"]

    def __init__(self, llm: LLMService):
        self.llm = llm
        self._rag_patterns = [re.compile(p, re.IGNORECASE) for p in RAG_PATTERNS]
        self._symptom_patterns = [re.compile(p, re.IGNORECASE) for p in SYMPTOM_PATTERNS]

    def classify(self, question: str, context: str = "", recent_intent: str = "") -> Dict:
        q = question.strip()
        q_lower = q.lower()

        if not q:
            return {"intent": "CHAT", "confidence": 0.2, "reason": "empty"}

        # ── Context-aware follow-up ──
        if recent_intent in self.INTENTS:
            follow_up_kw = [
                "còn", "vậy", "thế", "tiếp", "nó", "điều đó", "nữa",
                "vay", "the", "tiep", "no", "dieu do", "nua",
                "con nua", "còn nữa", "and", "then", "sau đó", "sau do",
                "thế còn", "the con", "vậy còn", "co nghia la",
                "nghĩa là", "tức là", "tuc la",
            ]
            word_count = len(q_lower.split())
            if word_count <= 5 and any(kw in q_lower for kw in follow_up_kw):
                return {"intent": recent_intent, "confidence": 0.85, "reason": "follow_up_context"}
            if word_count <= 3 and recent_intent in {"RAG", "SYMPTOM", "CHAT"}:
                return {"intent": recent_intent, "confidence": 0.78, "reason": "short_follow_up"}

        # ── Use LLM as primary classifier ──
        result = self._llm_classify(q, context)
        if result:
            return result

        # ── Fallback: rule-based when LLM fails ──
        return self._rule_fallback(q, q_lower)

    def _llm_classify(self, q: str, context: str) -> Dict | None:
        """Use LLM as the primary intent classifier."""
        try:
            prompt = PROMPT.format(
                q=q,
                context=context[:1000] if context else "No previous context.",
            )
            raw = self.llm.generate(prompt, temperature=0.0, max_tokens=150)
            data = self._extract_json(raw)
            if data:
                intent = str(data.get("intent", "")).upper()
                confidence = min(0.98, float(data.get("confidence", 0.5)))
                if intent in self.INTENTS:
                    return {
                        "intent": intent,
                        "confidence": confidence,
                        "reason": "llm_primary",
                    }
        except Exception:
            pass
        return None

    def _rule_fallback(self, q: str, q_lower: str) -> Dict:
        """Rule-based fallback when LLM classification fails."""
        rag_matches = sum(1 for p in self._rag_patterns if p.search(q_lower))
        symptom_matches = sum(1 for p in self._symptom_patterns if p.search(q_lower))

        # Planner keywords
        planner_kw = ["nhắc", "nhac", "remind", "plan", "task", "todo", "lịch", "lich",
                      "kế hoạch", "ke hoach", "uống thuốc", "uong thuoc",
                      "hẹn", "hen", "appointment", "schedule", "công việc", "cong viec",
                      "thêm", "them", "việc", "viec", "tạo", "tao", "nhac nho",
                      "nhắc nhở", "thong bao", "thông báo", "deadline",
                      "việc cần", "viec can", "cần làm", "can lam"]
        planner_score = sum(1 for kw in planner_kw if kw in q_lower)

        # Chat keywords
        chat_kw = ["chào", "chao", "hello", "hi", "bye", "cảm ơn", "cam on", "thanks",
                   "thời tiết", "thoi tiet", "weather", "mấy giờ", "may gio",
                   "bạn là ai", "ban la ai", "bạn tên gì", "ban ten gi"]
        chat_score = sum(1 for kw in chat_kw if kw in q_lower)

        scores = {
            "RAG": rag_matches * 2,
            "SYMPTOM": symptom_matches * 3,
            "PLANNER": planner_score * 2 + (3 if any(kw in q_lower for kw in ["nhắc", "task", "todo"]) else 0),
            "CHAT": chat_score * 2 + (1 if len(q_lower.split()) <= 3 else 0),
        }

        best = max(scores, key=scores.get)
        best_val = scores[best]
        second_val = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0

        if best_val == 0:
            # Pure fallback: short → CHAT, longer → RAG
            if len(q_lower.split()) <= 4:
                return {"intent": "CHAT", "confidence": 0.5, "reason": "fallback_short"}
            return {"intent": "RAG", "confidence": 0.4, "reason": "fallback_long"}

        confidence = min(0.85, 0.55 + 0.08 * best_val)
        if best_val >= second_val + 2:
            return {"intent": best, "confidence": confidence, "reason": f"rule_{best}"}

        # Tie → default to CHAT for short, RAG for long
        if len(q_lower.split()) <= 3:
            return {"intent": "CHAT", "confidence": 0.5, "reason": "tie_short"}
        return {"intent": "RAG", "confidence": 0.5, "reason": "tie_long"}

    @staticmethod
    def _extract_json(raw: str) -> Dict | None:
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