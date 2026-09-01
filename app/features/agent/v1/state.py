from typing import Annotated

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.features.agent.v1.schemas import DocumentWithSource, OutputFeedback, UserIntent


class GraphState(BaseModel):
    user_question: str
    is_input_safe: bool | None = None
    intent: UserIntent | None = None
    rewritten_user_question: str | None = None
    is_retrieval_sufficient: bool | None = None
    retrieval_results: str | None = None
    documents_with_sources: list[DocumentWithSource] | None = None
    web_search_results: str | None = None
    synthesis_response: str | None = None
    is_output_safe: bool | None = None
    output_guardrail_feedback: list[OutputFeedback] | None = None
    messages: Annotated[list, add_messages] = Field(default_factory=list)
