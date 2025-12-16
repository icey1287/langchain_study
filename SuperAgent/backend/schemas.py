from pydantic import BaseModel
from typing import Optional, List


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"
    session_id: Optional[str] = "default_session"


class ChatResponse(BaseModel):
    response: str


class MessageInfo(BaseModel):
    type: str
    content: str
    timestamp: str


class SessionMessagesResponse(BaseModel):
    messages: List[MessageInfo]


class SessionInfo(BaseModel):
    session_id: str
    updated_at: str
    message_count: int


class SessionListResponse(BaseModel):
    sessions: List[SessionInfo]
