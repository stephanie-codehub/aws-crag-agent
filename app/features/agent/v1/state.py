from enum import StrEnum, auto
from typing import Annotated, Literal

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class OutputFeedback(BaseModel):
    guardrail: Literal[
        "PII_sensitive_data", "toxicity_bias", "hallucination", "internal_architecture"
    ]
    reason: str


class UserIntent(StrEnum):
    GENERAL = auto()
    OUT_OF_SCOPE = auto()


class DocumentWithSource(BaseModel):
    content: str
    file: str
    page: int


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
