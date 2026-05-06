from __future__ import annotations

from app.graphs.healthcare_graph import HealthcareGraph


def _format_routing(routing: dict[str, object]) -> dict[str, object]:
    return {
        "intent": routing.get("intent", "CHAT"),
        "confidence": float(routing.get("confidence", 0.0)),
        "reason": routing.get("reason", ""),
    }


class HealthcareAgent:
    def __init__(self) -> None:
        self.graph = HealthcareGraph()

    def chat(self, user_id: str, message: str) -> dict[str, object]:
        result = self.graph.run(user_id, message)
        response = str(result.get("response", ""))
        routing = _format_routing(result.get("routing", {}))

        return {
            "response": response,
            "routing": routing,
            "user_id": user_id,
        }
