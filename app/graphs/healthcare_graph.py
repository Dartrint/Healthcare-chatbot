from __future__ import annotations

import re
from typing import Any, Dict
from langgraph.graph import StateGraph

from app.services.memory import VectorMemoryService
from app.services.planner import clear_plan, delete_task, get_plan, update_plan
from app.services.rag import RAGService
from app.services.router import RouterService
from app.services.symptom import SymptomService
from app.services.llm import LLMService
from app.services.mcp_gateway import MCPGateway
from app.services.tracer import trace_chain


INTENT_BRANCH = {
    "RAG": "rag",
    "SYMPTOM": "symptom",
    "PLANNER": "planner",
    "CHAT": "chat",
}


def _clean(text: Any) -> str:
    return text.strip() if isinstance(text, str) else ""


class HealthcareGraph:
    def __init__(self) -> None:
        self.llm = LLMService()
        self.router = RouterService(self.llm)
        self.rag = RAGService()
        self.symptom = SymptomService(self.llm)
        self.mcp = MCPGateway()

        self.graph = self._build_graph().compile()

    def _build_graph(self) -> StateGraph:
        g = StateGraph(dict)

        g.add_node("route", self._route)
        g.add_node("rag", self._rag)
        g.add_node("symptom", self._symptom)
        g.add_node("planner", self._planner)
        g.add_node("chat", self._chat)

        g.set_entry_point("route")
        g.add_conditional_edges("route", self._branch)

        for node in ["rag", "symptom", "planner", "chat"]:
            g.set_finish_point(node)

        return g

    def _route(self, state: Dict[str, Any]) -> Dict[str, Any]:
        user_input = _clean(state.get("user_input"))
        user_id = _clean(state.get("user_id", "user_1"))

        memory_service = VectorMemoryService(user_id)
        history = memory_service.get_all()[-6:]
        chat_context = "\n".join(
            f"User: {h['user']}\nAssistant: {h['bot']}"
            for h in history
        )
        related_memory = memory_service.search(user_input, k=3)
        memory_context = "\n".join(
            f"- User: {m.get('user', '')}\n  Assistant: {m.get('bot', '')}"
            for m in related_memory
        )
        recent_intent = history[-1].get("intent", "") if history else ""

        routing = self.router.classify(user_input, chat_context, recent_intent=recent_intent)
        intent = routing["intent"]
        confidence = routing["confidence"]

        state.update({
            "user_input": user_input,
            "user_id": user_id,
            "chat_context": chat_context,
            "memory_context": memory_context,
            "routing": {"intent": intent, "confidence": confidence, "reason": routing.get("reason", "")},
        })

        return state

    def _branch(self, state: Dict[str, Any]) -> str:
        intent = state.get("routing", {}).get("intent", "CHAT")
        return INTENT_BRANCH.get(intent, "chat")

    def _rag(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Medical knowledge: disease definitions, medications, treatments using RAG + web search."""
        query = state["user_input"]
        docs = self.rag.retrieve(query, k=5)
        external_context = self.mcp.query("medical_knowledge", query)
        web_results = self.mcp.query("web_search", f"medical health {query}")

        prompt = f"""Bạn là trợ lý y tế chuyên nghiệp. Trả lời ngắn gọn, chính xác bằng tiếng Việt dựa trên tài liệu y khoa được cung cấp.

Tài liệu tham khảo:
{chr(10).join(f"- {d}" for d in docs) if docs else "Không có tài liệu phù hợp."}

Thông tin bổ sung:
{external_context if external_context else "Không có thông tin bổ sung."}

Kết quả tìm kiếm web (thông tin mới nhất):
{web_results if web_results else "Không có kết quả tìm kiếm web."}

Lịch sử hội thoại:
{state.get("memory_context", "")}

Câu hỏi: {query}

Trả lời:
"""

        response = self.llm.generate(prompt, max_tokens=1024, temperature=0.3)
        state["response"] = response
        return state

    def _symptom(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze personal symptoms and provide health advice."""
        context = f"{state.get('chat_context', '')}\n{state.get('memory_context', '')}"
        state["response"] = self.symptom.analyze(
            state["user_input"],
            context
        )
        return state

    def _planner(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task/reminder management. Chat is ONLY for creating tasks.
        Delete/complete/view operations are handled via buttons in the UI.
        """
        query = state["user_input"]
        user_id = state["user_id"]
        q = query.lower()

        # Nếu người dùng muốn xem kế hoạch → hướng dẫn xem ở sidebar
        if any(x in q for x in ["show", "list", "xem", "lịch", "lich", "kế hoạch", "ke hoach"]):
            items = get_plan(user_id)
            if items:
                lines = []
                for i, it in enumerate(items):
                    icon = "✅" if it["status"] == "completed" else "⏳"
                    lines.append(f"{i+1}. {icon} **{it['task']}** — {it['date']} ({it['priority']})")
                state["response"] = "📋 **Kế hoạch của bạn:**\n\n" + "\n".join(lines) + \
                    "\n\n💡 *Dùng các nút 🗑️/✅ trong sidebar để xoá hoặc hoàn thành task.*"
            else:
                state["response"] = "📋 Bạn chưa có kế hoạch nào. Hãy nói *'Nhắc tôi...'* để tạo mới."
            return state

        # Nếu đề cập đến xoá → hướng dẫn dùng button
        if any(x in q for x in ["delete", "remove", "xóa", "xoa"]):
            items = get_plan(user_id)
            if not items:
                state["response"] = "📋 Không có kế hoạch nào để xoá."
                return state
            state["response"] = "🗑️ Bạn có thể xoá task trực tiếp bằng nút **🗑️** trong bảng Plan (sidebar bên trái)."
            return state

        # Nếu đề cập đến hoàn thành → hướng dẫn dùng button
        if any(x in q for x in ["complete", "done", "hoàn thành", "xong", "done"]):
            items = get_plan(user_id)
            if not items:
                state["response"] = "📋 Không có task nào để hoàn thành."
                return state
            state["response"] = "✅ Bạn có thể đánh dấu task hoàn thành bằng nút **✅** trong bảng Plan (sidebar bên trái)."
            return state

        # Tạo task mới (mặc định)
        state["response"] = update_plan(user_id, query)
        return state

    def _chat(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Non-medical conversation: use MCP tools for external data + LLM native knowledge."""
        query = state["user_input"]

        # Collect MCP tool data (may be empty if Tavily not configured)
        weather_info = self.mcp.query("weather", query)
        time_info = self.mcp.query("time_date", query)
        web_info = self.mcp.query("web_search", query)

        # Build context lines only for non-empty data
        tool_parts = []
        if weather_info:
            tool_parts.append(f"- Thời tiết: {weather_info}")
        if time_info:
            tool_parts.append(f"- Thời gian: {time_info}")
        if web_info:
            tool_parts.append(f"- Tra cứu web: {web_info}")

        tool_context = "\n".join(tool_parts)
        tool_section = f"\nDữ liệu tra cứu:\n{tool_context}\n" if tool_context else ""

        system_prompt = f"""Bạn là trợ lý AI thông minh, thân thiện, vui vẻ. Trả lời bằng tiếng Việt tự nhiên, chính xác.

Khả năng của bạn:
- **Trò chuyện xã giao** — chào hỏi, cảm ơn, tạm biệt, khen ngợi
- **Kiến thức tổng hợp** — lịch sử, khoa học, công nghệ, văn hóa, ẩm thực, thể thao, giải trí. Dùng kiến thức vốn có của bạn để trả lời.
- **Thời tiết & thời gian** — dùng dữ liệu thực tế từ công cụ nếu có
- **Tra cứu thông tin thời gian thực** — dùng kết quả web (nếu có)
- **Tư vấn đời sống** — công việc, học tập, kỹ năng mềm, tâm lý

⚠️ KHÔNG trả lời câu hỏi y tế, chuẩn đoán, thuốc men. Nếu người dùng hỏi về y tế, hãy hướng dẫn họ đặt câu hỏi y tế cụ thể.
{tool_section}
Lịch sử trò chuyện:
{state.get("chat_context", "")}

Ký ức về người dùng:
{state.get("memory_context", "")}

Người dùng: {query}
Trả lời:"""

        response = self.llm.generate(system_prompt, max_tokens=1024, temperature=0.7)
        state["response"] = response
        return state

    @trace_chain
    def run(self, user_id: str, user_input: str) -> Dict[str, Any]:
        result = self.graph.invoke({
            "user_id": user_id,
            "user_input": user_input
        })

        response = result.get("response", "")
        intent = str(result.get("routing", {}).get("intent", ""))

        # save memory
        VectorMemoryService(user_id).add(user_input, response, intent=intent)

        return result