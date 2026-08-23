import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_question: str
    session_id: uuid.UUID


class UpdateChatTitleRequest(BaseModel):
    title: str = Field(max_length=100)
