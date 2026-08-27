from typing import Annotated

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.features.agent.v1.schemas import DocumentWithSource, OutputFeedback, UserIntent


class GraphState(BaseModel):
    user_question: str
    is_input_safe: bool
    intent: UserIntent
    rewritten_user_question: str
    is_retrieval_sufficient: bool
    retrieval_results: str
    documents_with_sources: list[DocumentWithSource]
    web_search_results: str
    synthesis_response: str
    is_output_safe: bool
    output_guardrail_feedback: list[OutputFeedback]
    messages: Annotated[list, add_messages] = Field(default_factory=list)
