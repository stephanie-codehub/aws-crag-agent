import uuid
from datetime import datetime

from pydantic import BaseModel

from app.features.chats.v1.schemas.enums import MessageRole


class InitSessionResponse(BaseModel):
    session_id: uuid.UUID


class ChatResponse(BaseModel):
    content: str
    timestamp: datetime
    session_id: uuid.UUID


class ChatSessionInfo(BaseModel):
    session_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    id: uuid.UUID
    role: MessageRole
    content: str
    timestamp: datetime


class ChatSessionFull(BaseModel):
    session_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessage] = []
