# Simple in-memory chat history

from typing import Dict, List

# { user_id: [ {user: "...", bot: "..."} ] }
_sessions: Dict[str, List[dict]] = {}


def get_chat_history(user_id: str) -> List[dict]:
    return _sessions.get(user_id, [])


def add_chat(user_id: str, user: str, bot: str) -> None:
    _sessions.setdefault(user_id, []).append({
        "user": user,
        "bot": bot
    })


def clear_chat(user_id: str) -> None:
    _sessions.pop(user_id, None)