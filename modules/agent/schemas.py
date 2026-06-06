from __future__ import annotations
from typing import TypedDict
from pydantic import BaseModel


class AgentState(TypedDict, total=False):
    query:       str
    session_id:  str
    user_id:     int
    intent:      dict
    listings:    list
    history:     list
    retry_count: int
    comparison:  str | None
    response:    str | None
    errors:      list[str]
    _regen:      bool  # internal flag: validate_comparison requests regeneration


class ChatRequest(BaseModel):
    query:      str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response:   str
    session_id: str


class TranscribeResponse(BaseModel):
    text: str


class FeedbackRequest(BaseModel):
    session_id:  str
    turn_index:  int = 0
    rating:      int   # 1 = thumbs up, -1 = thumbs down


class FeedbackResponse(BaseModel):
    saved: bool
