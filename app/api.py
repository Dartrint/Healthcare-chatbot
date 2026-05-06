from __future__ import annotations

import json
import json
import time
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.agents.healthcare_agent import HealthcareAgent
from app.config import PLANS_FILE, MEMORY_DIR
from app.schemas import ChatRequest, ChatResponse, CompleteTaskRequest
from app.services.memory import VectorMemoryService, safe_id
from app.services.planner import clear_plan, complete_task, delete_task, get_plan, get_due_reminders
from app.services.quality_metrics import QualityMetricsCalculator, SystemMetrics
from pathlib import Path

app = FastAPI(
    title="Healthcare AI Agent API",
    version="4.0.0",
    description="Production-ready healthcare agent built with LangChain and LangGraph.",
)

@app.get("/")
def root() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "healthcare-agent",
        "endpoints": {
            "health": "GET /health",
            "chat": "POST /chat",
            "plan_view": "GET /plan/{user_id}",
            "plan_complete": "POST /plan/complete",
            "reminders": "GET /reminders/{user_id}",
            "memory": "GET /memory/{user_id}",
            "metrics": "GET /metrics",
            "clear_memory": "DELETE /memory/{user_id}",
        },
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = HealthcareAgent()
quality_calculator = QualityMetricsCalculator()
system_metrics = SystemMetrics()


@app.middleware("http")
async def add_process_time_middleware(request: Request, call_next):
    """Middleware to track request processing time and record metrics."""
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    
    if response.status_code < 400:
        system_metrics.record_request(duration_ms, success=True)
    else:
        system_metrics.record_request(duration_ms, success=False)
    
    response.headers["X-Process-Time"] = str(duration_ms)
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "healthcare-agent"}


def _load_plan_index() -> dict[str, list[dict[str, str]]]:
    if not PLANS_FILE.exists():
        return {}

    try:
        with PLANS_FILE.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


@app.get("/metrics")
def metrics() -> dict[str, object]:
    """Get comprehensive system and quality metrics."""
    plan_index = _load_plan_index()
    memory_files = [path.name for path in MEMORY_DIR.glob("*.json")]
    system_summary = system_metrics.get_summary()

    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "system": system_summary,
        "data": {
            "users_with_plans": len(plan_index),
            "total_plan_items": sum(len(tasks) for tasks in plan_index.values()),
            "users_with_memory": len(memory_files),
        },
    }


@app.get("/chat")
def chat_info(user_id: str | None = None, message: str | None = None) -> dict[str, object]:
    if user_id and message:
        try:
            return agent.chat(user_id, message)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    return {
        "detail": "Use POST /chat with JSON body {\"user_id\": \"...\", \"message\": \"...\"}. Or provide user_id and message query parameters to chat directly.",
        "sample_json": {
            "user_id": "user_1",
            "message": "Em bị đau đầu và mệt mỏi",
        },
        "sample_query": "/chat?user_id=user_1&message=Em+bi+%C4%91au+%C4%91%E1%BA%A7u+v%C3%A0+m%E1%BB%B9t+m%E1%BB%91i",
    }


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> dict[str, object]:
    """Chat endpoint with quality metrics tracking."""
    try:
        start_time = time.time()
        result = agent.chat(request.user_id, request.message)
        response_time_ms = (time.time() - start_time) * 1000
        
        response_text = result.get("response", "")
        quality = quality_calculator.calculate_quality(
            query=request.message,
            response=response_text,
            response_time_ms=response_time_ms,
        )
        
        system_metrics.record_quality_score(quality.overall_score())
        system_metrics.user_sessions.add(request.user_id)
        
        result["metrics"] = {
            "quality": quality.to_dict(),
            "overall_score": quality.overall_score(),
            "response_time_ms": round(response_time_ms, 2),
        }
        
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/plan/{user_id}")
def view_plan(user_id: str) -> dict[str, object]:
    plan = get_plan(user_id)
    return {
        "user_id": user_id,
        "total": len(plan),
        "pending": sum(1 for item in plan if item.get("status") == "pending"),
        "completed": sum(1 for item in plan if item.get("status") == "completed"),
        "items": plan,
    }


@app.get("/plan/complete")
def complete_plan_info() -> dict[str, object]:
    return {
        "detail": "Use POST /plan/complete with JSON body {\"user_id\": \"...\", \"task_id\": \"...\"}",
    }


@app.post("/plan/complete")
def complete_plan(request: CompleteTaskRequest) -> dict[str, str]:
    return {"message": complete_task(request.user_id, request.task_id)}


@app.delete("/plan/{user_id}/{task_id}")
def delete_plan_task(user_id: str, task_id: str) -> dict[str, str]:
    return {"message": delete_task(user_id, task_id)}


@app.delete("/plan/{user_id}")
def clear_user_plan(user_id: str) -> dict[str, str]:
    return {"message": clear_plan(user_id)}


@app.get("/reminders/{user_id}")
def reminders(user_id: str) -> dict[str, object]:
    due = get_due_reminders(user_id)
    return {
        "user_id": user_id,
        "due_today": len(due),
        "items": due,
    }


@app.get("/memory/{user_id}")
def view_memory(user_id: str, limit: int = 10) -> dict[str, object]:
    memory = VectorMemoryService(user_id)
    entries = memory.get_all()[-limit:]
    return {
        "user_id": user_id,
        "total_exchanges": len(memory.get_all()),
        "recent": entries,
    }


@app.delete("/memory/{user_id}")
def clear_memory(user_id: str) -> dict[str, str]:
    sid = safe_id(user_id)
    for suffix in [".faiss", ".json"]:
        path = Path(f"memory_store/{sid}{suffix}")
        if path.exists():
            path.unlink()
    return {"message": f"Memory cleared for {user_id}"}
