"""Pydantic model for tool creation requests."""
from __future__ import annotations

import time
import uuid
from typing import Literal

from pydantic import BaseModel, Field


Priority = Literal["low", "mid", "high"]
Status = Literal["pending", "pushed", "complete", "failed"]

_PRIORITY_RANK: dict[str, int] = {"high": 0, "mid": 1, "low": 2}


class ToolRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    intent: str
    user_query: str
    speaker: str = "unknown"
    priority: Priority = "mid"
    status: Status = "pending"
    context: list[dict] = Field(default_factory=list)
    error: str | None = None

    @property
    def priority_rank(self) -> int:
        return _PRIORITY_RANK[self.priority]
