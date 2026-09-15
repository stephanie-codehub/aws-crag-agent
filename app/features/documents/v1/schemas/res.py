import uuid
from datetime import datetime

from pydantic import BaseModel

from app.features.chats.v1.schemas.enums import IndexingStatus


class IndexStat(BaseModel):
    start_time: datetime
    stop_time: datetime | None
    job_id: uuid.UUID
    status: IndexingStatus
    num_added: int | None
    num_updated: int | None
    num_skipped: int | None
    num_deleted: int | None
