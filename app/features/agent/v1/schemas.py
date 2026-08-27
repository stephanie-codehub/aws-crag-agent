from enum import StrEnum, auto
from typing import Literal

from pydantic import BaseModel, Field


class UserIntent(StrEnum):
    GENERAL = auto()
    ERROR_DIAGNOSIS = auto()
    PROVISIONING = auto()
    OUT_OF_SCOPE = auto()


class IntentSchema(BaseModel):
    intent: UserIntent = Field(
        description="The primary intent category of the user prompt."
        "ERROR_DIAGNOSIS- AWS EC2 questions related to error diagnosis"
        "PROVISIONING- AWS EC2 questions non related to error diagnosis"
        "general- This includes pleasantries and greetings only"
        "out_of_scope- User query is unrelated to the AWS EC2 domain"
    )


class RewrittenQueryOutput(BaseModel):
    rag_query: str = Field(
        description="Optimized keyword string explicitly tuned for semantic matching inside a local vector database."
    )
    web_search_query: str = Field(
        description="Concise keyword query optimized for fetching current, real-time data from an open internet search engine."
    )


class OutputFeedback(BaseModel):
    guardrail: Literal[
        "PII_sensitive_data", "toxicity_bias", "hallucination", "internal_architecture"
    ]
    reason: str


class DocumentWithSource(BaseModel):
    content: str
    file: str
    page: int
