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
    if any(token in normalized for token in ["today", "hôm nay", "hom nay"]):
        return today.strftime("%Y-%m-%d")
    if any(token in normalized for token in ["tomorrow", "ngày mai", "ngay mai"]):
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if any(token in normalized for token in ["next week", "tuần tới", "tuan toi"]):
        return (today + timedelta(weeks=1)).strftime("%Y-%m-%d")
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    return today.strftime("%Y-%m-%d")


def _parse_priority(text: str) -> str:
    normalized = text.lower()
    if any(token in normalized for token in ["urgent", "asap", "emergency", "khẩn", "khan", "ngay", "gấp", "gap"]):
        return "high"
    if any(token in normalized for token in ["important", "quan trọng", "quan trong"]):
        return "medium"
    return "low"


def update_plan(user_id: str, task_description: str, date_override: str | None = None, priority_override: str | None = None) -> str:
    plans = _load_plans()
    user_plan = plans.get(user_id, [])
    date = date_override if date_override else _parse_date(task_description)
    priority = priority_override if priority_override else _parse_priority(task_description)
    task_clean = re.sub(
        r"\b(today|tomorrow|next week|urgent|asap|hôm nay|ngày mai|tuần tới|ngay|khẩn|quan trọng)\b",
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
        f"✅ Đã thêm: {entry['task']}\n"
        f"📅 Ngày: {entry['date']}\n"
        f"{emoji[priority]} Ưu tiên: {priority.upper()}\n"
        f"📌 Tổng số: {len(user_plan)}"
    )


def update_task(user_id: str, task_id: str, task_text: str | None = None, date: str | None = None, priority: str | None = None) -> str:
    """Edit an existing task."""
    plans = _load_plans()
    user_plan = plans.get(user_id, [])
    for t in user_plan:
        if t.get("id") == task_id:
            if task_text:
                t["task"] = task_text
            if date:
                t["date"] = date
            if priority:
                t["priority"] = priority
            plans[user_id] = user_plan
            _save_plans(plans)
            return f"✅ Đã cập nhật: {t['task']}"
    return "⚠️ Không tìm thấy task."


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
            return f"✅ Đã hoàn thành: {task['task']}"
    return "⚠️ Không tìm thấy task."


def delete_task(user_id: str, task_id: str) -> str:
    plans = _load_plans()
    user_plan = plans.get(user_id, [])
    next_plan = [task for task in user_plan if task.get("id") != task_id]
    if len(next_plan) == len(user_plan):
        return "⚠️ Không tìm thấy task."
    plans[user_id] = next_plan
    _save_plans(plans)
    return "🗑️ Đã xoá task."


def batch_complete_tasks(user_id: str, task_ids: list[str]) -> str:
    plans = _load_plans()
    user_plan = plans.get(user_id, [])
    count = 0
    for task in user_plan:
        if task.get("id") in task_ids and task.get("status") == "pending":
            task["status"] = "completed"
            task["completed_at"] = datetime.utcnow().isoformat()
            count += 1
    if count:
        plans[user_id] = user_plan
        _save_plans(plans)
        return f"✅ Đã hoàn thành {count} task."
    return "⚠️ Không có task pending."


def batch_delete_tasks(user_id: str, task_ids: list[str]) -> str:
    plans = _load_plans()
    user_plan = plans.get(user_id, [])
    before = len(user_plan)
    ids_set = set(task_ids)
    user_plan = [t for t in user_plan if t.get("id") not in ids_set]
    removed = before - len(user_plan)
    if removed:
        plans[user_id] = user_plan
        _save_plans(plans)
        return f"🗑️ Đã xoá {removed} task."
    return "⚠️ Không có task nào để xoá."


def clear_plan(user_id: str) -> str:
    plans = _load_plans()
    removed = len(plans.get(user_id, []))
    plans[user_id] = []
    _save_plans(plans)
    return f"🧹 Đã xoá {removed} task."


def get_due_reminders(user_id: str) -> list[dict[str, str]]:
    today = datetime.today().strftime("%Y-%m-%d")
    plans = _load_plans()
    user_plan = plans.get(user_id, [])
    due: list[dict[str, str]] = []
    for task in user_plan:
        if task.get("date") == today and task.get("status") == "pending":
            due.append(task)
    return due