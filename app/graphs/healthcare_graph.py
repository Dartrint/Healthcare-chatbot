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

    # =========================
    # GRAPH
    # =========================
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

    # =========================
    # ROUTER (HYBRID)
    # =========================
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
            "routing": {"intent": intent, "confidence": confidence},
        })

        return state

    def _branch(self, state: Dict[str, Any]) -> str:
        intent = state.get("routing", {}).get("intent", "CHAT")
        return INTENT_BRANCH.get(intent, "chat")

    # =========================
    # NODES
    # =========================
    def _rag(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state["user_input"]
        docs = self.rag.retrieve(query, k=5)
        external_context = self.mcp.query("medical_knowledge", query)

        prompt = f"""
You are a medical assistant.

Docs:
{chr(10).join(f"- {d}" for d in docs)}

MCP context:
{external_context}

Relevant memory:
{state.get("memory_context", "")}

Question: {query}

Answer clearly and safely. Add disclaimer.
"""

        state["response"] = self.llm.generate(prompt, max_tokens=300)
        return state

    def _symptom(self, state: Dict[str, Any]) -> Dict[str, Any]:
        state["response"] = self.symptom.analyze(
            state["user_input"],
            f"{state.get('chat_context', '')}\n{state.get('memory_context', '')}"
        )
        return state

    def _planner(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state["user_input"]
        user_id = state["user_id"]
        q = query.lower()

        if any(x in q for x in ["clear plan", "xóa hết", "xoa het", "xóa toàn bộ", "xoa toan bo"]):
            state["response"] = clear_plan(user_id)
            return state

        if any(x in q for x in ["delete", "remove", "xóa", "xoa"]):
            items = get_plan(user_id)
            if not items:
                state["response"] = "📋 No plan found."
                return state

            # delete by sequence number: "xoa task 2"
            number_match = re.search(r"\b(\d+)\b", q)
            if number_match:
                idx = int(number_match.group(1)) - 1
                if 0 <= idx < len(items):
                    state["response"] = delete_task(user_id, items[idx]["id"])
                else:
                    state["response"] = "⚠️ Invalid task number."
                return state

            # delete by task id
            id_match = re.search(r"\b[0-9a-f]{8}-[0-9a-f-]{27}\b", q)
            if id_match:
                state["response"] = delete_task(user_id, id_match.group(0))
                return state

            state["response"] = "⚠️ Please provide task number or task id to delete."
            return state

        if any(x in q for x in ["show", "list", "xem", "plan"]):
            items = get_plan(user_id)
            if items:
                text = "\n".join(f"{i+1}. {it['task']} ({it['status']})" for i, it in enumerate(items))
                state["response"] = f"📋 Plan:\n{text}"
            else:
                state["response"] = "📋 No plan found."
        else:
            state["response"] = update_plan(user_id, query)

        return state

    def _chat(self, state: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
You are a friendly healthcare assistant.

Recent chat context:
{state.get("chat_context", "")}

Conversation memory:
{state.get("memory_context", "")}

User: {state["user_input"]}
"""

        state["response"] = self.llm.generate(prompt, max_tokens=200)
        return state

    # =========================
    # RUN
    # =========================
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