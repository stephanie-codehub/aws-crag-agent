from langgraph.graph import END

from app.features.agent.v1.schemas import UserIntent
from app.features.agent.v1.state import GraphState


def is_input_safe_router(state: GraphState):
    if state.is_input_safe:
        return "intent_classifier_node"
    else:
        return "fallback_node"


def intent_router(state: GraphState):
    if state.intent == UserIntent.GENERAL:
        return "generator_node"
    elif state.intent == UserIntent.ERROR_DIAGNOSIS or UserIntent.PROVISIONING:
        return "query_rewriter_node"
    else:
        return "fallback_node"


def is_output_safe_router(state: GraphState):
    if state.is_output_safe:
        return END
    else:
        return "generator_node"
