import uuid

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse

from app.features.agent.v1.graph import invoke_agent, stream_agent
from app.features.chats.v1.schemas.req import (
    ChatRequest,
)
from app.features.chats.v1.schemas.res import (
    InitSessionResponse,
)

chat_router = APIRouter()


@chat_router.post("/new", response_model=InitSessionResponse)
async def get_new_session_id():
    new_id = str(uuid.uuid4())
    return {"session_id": new_id}


@chat_router.post("/chat/invoke")
async def chat_invoke(request: ChatRequest):
    response = await invoke_agent(request.user_question, request.session_id)
    return {"response": response}


@chat_router.post("/stream")
async def chat_stream(request: ChatRequest):
    return EventSourceResponse(stream_agent(request.user_question, request.session_id))
