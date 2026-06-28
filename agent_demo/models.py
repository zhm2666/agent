"""Pydantic 请求/响应模型 —— 用 Optional 兼容 Python 3.8+"""

from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    text: str
    session_id: Optional[str] = None


class ReviewRequest(BaseModel):
    thread_id: str
    decision: str  # "retry" 或 "approve"


class ChatResponse(BaseModel):
    status: str  # "completed" 或 "waiting_for_review"
    translation: Optional[str] = None
    attempts: Optional[int] = None
    quality: Optional[str] = None
    review_data: Optional[dict] = None
    message: Optional[str] = None


class ReviewResponse(BaseModel):
    status: str
    translation: Optional[str] = None
    attempts: Optional[int] = None
    quality: Optional[str] = None
    human_decision: Optional[str] = None
    message: Optional[str] = None


class SessionInfo(BaseModel):
    session_id: str
    thread_id: str
    created_at: str