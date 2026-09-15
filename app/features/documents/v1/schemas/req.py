from pydantic import BaseModel, Field

from app.features.documents.v1.schemas.enums import (
    IndexingStatus,
)


class IndexStatFilterParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    status: IndexingStatus | None = None
