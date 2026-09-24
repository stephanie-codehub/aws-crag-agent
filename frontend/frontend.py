import uuid

import chainlit as cl
from chainlit.types import ThreadDict

from app.features.agent.v1.graph import stream_agent


@cl.on_chat_start
async def on_chat_start():
    """Configure session ID and workflow instance"""
    session_id = cl.user_session.get("id")
    cl.user_session.set("session_id", session_id)
    await cl.Message(content="Hello! I am ready to chat.").send()


async def ask_agent(prompt: str, session_id: uuid.UUID):
    cb = cl.LangchainCallbackHandler(stream_final_answer=True)

    res = cl.Message(content="")

    async with cl.Step(name="Thinking...", show_input=False) as status_step:
        async for chunk in stream_agent(
            user_question=prompt,
            session_id=session_id,
            with_status=True,
            callbacks=[cb],
        ):
            if chunk["type"] == "status":
                status_step.name = f"{chunk['content']}..."
                await status_step.update()

            elif chunk["type"] == "token":
                await status_step.remove()
                await res.stream_token(chunk["content"])

    await res.send()


@cl.on_message
async def on_message(message: cl.Message):
    """Respond to user question"""
    session_id: uuid.UUID = uuid.UUID(cl.user_session.get("session_id"))
    await ask_agent(message.content, session_id)


@cl.on_chat_resume
async def on_chat_resume(session: ThreadDict):
    pass
