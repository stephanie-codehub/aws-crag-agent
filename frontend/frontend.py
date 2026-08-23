import uuid

import chainlit as cl
from chainlit.types import ThreadDict

from app.features.agent.v1.graph import stream_agent


@cl.on_chat_start
async def on_chat_start():
    """Configure session ID and workflow instance"""
    session_id = cl.user_session.get("id")
    cl.user_session.set("session_id", session_id)
    #  cl.user_session.set("chatbot", chatbot)
    await cl.Message(content="Hello! I am ready to chat.").send()


async def ask_agent(prompt: str):
    #  chatbot = cl.user_session.get("chatbot")

    res = cl.Message(content="")
    session_id: uuid.UUID = uuid.UUID(cl.user_session.get("session_id"))
    cb = cl.LangchainCallbackHandler(stream_final_answer=True)

    async for chunk in stream_agent(prompt, session_id, [cb]):
        await res.stream_token(chunk)
    await res.send()


@cl.on_message
async def on_message(message: cl.Message):
    """Respond to user question"""
    await ask_agent(message.content)


@cl.on_chat_resume
async def on_chat_resume(session: ThreadDict):
    pass
