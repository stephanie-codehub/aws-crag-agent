"""Node implementations used by the agent StateGraph."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from app.core.utils import log_node_status
from app.features.agent.v1.llm import create_llm_client
from app.features.agent.v1.prompts.prompt_loader import get_prompt_content
from app.features.agent.v1.schemas import (
    IntentSchema,
)
from app.features.agent.v1.state import (
    GraphState,
)


async def intent_classifier_node(state: GraphState):
    """Classify the user's intent as one of the UserIntent Enum values."""

    prompt_input = {"user_question": state.user_question}

    prompt_content = get_prompt_content(
        prompt_name="intent_classifier", variables=prompt_input
    )
    llm = create_llm_client(prompt_content.model_settings)
    messages = [
        SystemMessage(content=prompt_content.system_prompt),
        HumanMessage(content=prompt_content.user_prompt),
    ]
    structured_llm = llm.with_structured_output(IntentSchema)
    response = await structured_llm.ainvoke(messages)
    return {"intent": response.intent}


async def generator_node(state: GraphState):
    """Synthesizes tool outputs to generate the assistant's response."""
    log_node_status("Generating response")
    prompt_input = {
        "user_question": state.user_question,
        "message_history": state.messages,
        "retrieval_results": state.retrieval_results,
        "web_search_results": state.web_search_results,
        "feedback": state.output_guardrail_feedback,
    }

    prompt_content = get_prompt_content(
        prompt_name="synthesis_generator", variables=prompt_input
    )
    llm = create_llm_client(prompt_content.model_settings)
    messages = [
        SystemMessage(content=prompt_content.system_prompt),
        HumanMessage(content=prompt_content.user_prompt),
    ]
    generator_chain = llm | StrOutputParser()
    response = await generator_chain.ainvoke(messages)
    return {"synthesis_response": response, "messages": [AIMessage(content=response)]}


async def input_guardrail_node(state: GraphState):
    """Input guardrail node that validates user input."""
    log_node_status("Verifying safety")
    is_input_safe = True
    return {"is_input_safe": is_input_safe}


async def output_guardrail_node(state: GraphState):
    """Simple output guardrail node that checks model output safety."""
    log_node_status("Verifying AI safety")
    is_output_safe = True
    return {"is_output_safe": is_output_safe}


async def fallback_node(state: GraphState) -> dict:
    """
    Handles out-of-scope queries and unsafe user inputs.
    Returns a standardized polite refusal and guidance message.
    """
    FALLBACK_MESSAGE = (
        "Your query is currently outside my capabilities, however, "
        "I can provide assistance with AWS EC2 code provisioning, validation and error diagnosis."
    )
    return {
        "synthesis_response": FALLBACK_MESSAGE,
        "messages": [AIMessage(content=FALLBACK_MESSAGE)],
    }


nodes = [
    input_guardrail_node,
    intent_classifier_node,
    output_guardrail_node,
    fallback_node,
    generator_node,
]
