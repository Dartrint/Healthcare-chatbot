from __future__ import annotations

from app.services.llm import LLMService


class SymptomService:
    def __init__(self, llm: LLMService):
        self.llm = llm

    def analyze(self, user_input: str, context: str = "") -> str:
        prompt = f"""Bạn là trợ lý phân tích triệu chứng y tế. Hãy phân tích các triệu chứng của bệnh nhân bằng tiếng Việt.

Triệu chứng: {user_input}

Tiền sử/ngữ cảnh:
{context}

Hãy cung cấp:
1. **Nguyên nhân có thể** — Liệt kê 2-3 nguyên nhân thường gặp
2. **Mức độ nghiêm trọng** — Nhẹ/Trung bình/Nghiêm trọng
3. **Xử trí tại nhà** — Các biện pháp có thể tự làm
4. **Dấu hiệu nguy hiểm (Red Flags)** — Khi nào cần đi khám ngay

Trả lời bằng tiếng Việt, ngắn gọn dễ hiểu."""
        return self.llm.generate(prompt, max_tokens=600, temperature=0.3)