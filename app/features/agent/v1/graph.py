import uuid
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.features.agent.v1.nodes import nodes
from app.features.agent.v1.routers import (
    intent_router,
    is_input_safe_router,
    is_output_safe_router,
)
from app.features.agent.v1.state import GraphState

graph = StateGraph(GraphState)

for node in nodes:
    graph.add_node(node)

graph.add_edge(START, "input_guardrail_node")
graph.add_conditional_edges("input_guardrail_node", is_input_safe_router)
graph.add_conditional_edges("intent_classifier_node", intent_router)
graph.add_edge("generator_node", "output_guardrail_node")
graph.add_conditional_edges("output_guardrail_node", is_output_safe_router)
graph.add_edge("fallback_node", END)

memory_checkpointer = MemorySaver()
workflow = graph.compile(checkpointer=memory_checkpointer)


async def invoke_agent(
    user_question: str, session_id: uuid.UUID, callbacks: list | None = None
) -> str:
    config: RunnableConfig = {
        "configurable": {"thread_id": str(session_id)},
    }
    if callbacks:
        config["callbacks"] = callbacks

    inputs: Any = {
        "user_question": user_question,
        "messages": [HumanMessage(content=user_question)],
    }

    response = await workflow.ainvoke(input=inputs, config=config)
    return response["messages"][-1].content


async def stream_agent(
    user_question: str,
    session_id: uuid.UUID,
    callbacks: list[Any] | None = None,
    with_status: bool = False,
) -> AsyncGenerator[dict[str, str], None]:
    config: RunnableConfig = {
        "configurable": {"thread_id": str(session_id)},
    }
    if callbacks:
        config["callbacks"] = callbacks

    inputs: Any = {
        "user_question": user_question,
        "messages": [HumanMessage(content=user_question)],
    }

    stream_modes = ["messages"]
    if with_status:
        stream_modes.append("custom")

    async for chunk_type, chunk_data in workflow.astream(
        input=inputs,
        config=config,
        stream_mode=stream_modes,
    ):
        if chunk_type == "messages":
            msg, _ = chunk_data
            if isinstance(msg, AIMessageChunk) and msg.content:
                yield {"type": "token", "content": str(msg.content)}

        elif chunk_type == "custom":
            yield {"type": "status", "content": str(chunk_data)}
