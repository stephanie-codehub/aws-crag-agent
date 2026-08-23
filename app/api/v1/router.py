from fastapi import APIRouter

from app.features.chats.v1.router import chat_router

v1_router = APIRouter()


# PUBLIC ROUTES
v1_router.include_router(chat_router, prefix="/chats", tags=["Chat Management"])
