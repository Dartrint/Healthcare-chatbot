from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


class ChatRequest(BaseModel):
    user_id: str = Field(..., example="user_1")
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    response: str
    routing: dict[str, Any]
    user_id: str


class CompleteTaskRequest(BaseModel):
    user_id: str = Field(...)
    task_id: str = Field(...)


class DeleteManyTasksRequest(BaseModel):
    user_id: str = Field(...)
    indices: list[int] = Field(..., min_length=1, description="1-based task indices")
