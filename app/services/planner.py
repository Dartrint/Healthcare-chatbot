from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from app.config import MEMORY_DIR

PLANS_FILE = MEMORY_DIR / "plans.json"
PLANS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_plans() -> dict[str, list[dict[str, str]]]:
    if not PLANS_FILE.exists():
        return {}
    try:
        with PLANS_FILE.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def _save_plans(plans: dict[str, list[dict[str, str]]]) -> None:
    temp_file = PLANS_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as handle:
        json.dump(plans, handle, ensure_ascii=False, indent=2)
    temp_file.replace(PLANS_FILE)


def _parse_date(text: str) -> str:
    today = datetime.today()
    normalized = text.lower()
    if any(token in normalized for token in ["today", "hôm nay"]):
        return today.strftime("%Y-%m-%d")
    if any(token in normalized for token in ["tomorrow", "ngày mai"]):
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if any(token in normalized for token in ["next week", "tuần tới"]):
        return (today + timedelta(weeks=1)).strftime("%Y-%m-%d")
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    return today.strftime("%Y-%m-%d")


def _parse_priority(text: str) -> str:
    normalized = text.lower()
    if any(token in normalized for token in ["urgent", "asap", "emergency", "khẩn", "ngay"]):
        return "high"
    if any(token in normalized for token in ["important", "quan trọng"]):
        return "medium"
    return "low"


def update_plan(user_id: str, task_description: str) -> str:
    plans = _load_plans()
    user_plan = plans.get(user_id, [])
    date = _parse_date(task_description)
    priority = _parse_priority(task_description)
    task_clean = re.sub(
        r"\b(today|tomorrow|next week|urgent|asap|hôm nay|ngày mai|tuần tới)\b",
        "",
        task_description,
        flags=re.IGNORECASE,
    ).strip(" ,.")
    task_clean = task_clean or task_description
    entry = {
        "id": str(uuid.uuid4()),
        "task": task_clean,
        "date": date,
        "priority": priority,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }
    user_plan.append(entry)
    plans[user_id] = user_plan
    _save_plans(plans)
    emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    return (
        f"✅ Task added: {entry['task']}\n"
        f"📅 Date: {entry['date']}\n"
        f"{emoji[priority]} Priority: {priority.upper()}\n"
        f"📌 Total tasks: {len(user_plan)}"
    )


def get_plan(user_id: str) -> list[dict[str, str]]:
    plans = _load_plans()
    return plans.get(user_id, [])


def complete_task(user_id: str, task_id: str) -> str:
    plans = _load_plans()
    user_plan = plans.get(user_id, [])
    for task in user_plan:
        if task.get("id") == task_id:
            task["status"] = "completed"
            task["completed_at"] = datetime.utcnow().isoformat()
            plans[user_id] = user_plan
            _save_plans(plans)
            return f"✅ Completed: {task['task']}"
    return "⚠️ Task not found."


def delete_task(user_id: str, task_id: str) -> str:
    plans = _load_plans()
    user_plan = plans.get(user_id, [])
    next_plan = [task for task in user_plan if task.get("id") != task_id]
    if len(next_plan) == len(user_plan):
        return "⚠️ Task not found."
    plans[user_id] = next_plan
    _save_plans(plans)
    return "🗑️ Task deleted."


def clear_plan(user_id: str) -> str:
    plans = _load_plans()
    removed = len(plans.get(user_id, []))
    plans[user_id] = []
    _save_plans(plans)
    return f"🧹 Cleared {removed} task(s)."


def get_due_reminders(user_id: str) -> list[dict[str, str]]:
    today = datetime.today().strftime("%Y-%m-%d")
    plans = _load_plans()
    user_plan = plans.get(user_id, [])
    due: list[dict[str, str]] = []
    for task in user_plan:
        if task.get("date") == today and task.get("status") == "pending":
            due.append(task)
    return due
