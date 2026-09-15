import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.session import Base
from app.features.documents.v1.schemas.enums import IndexingStatus


class IndexStatRecord(Base):
    __tablename__ = "index_stat_records"
    job_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stop_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[IndexingStatus] = mapped_column(String(50), nullable=False)
    num_added: Mapped[int | None] = mapped_column()
    num_updated: Mapped[int | None] = mapped_column()
    num_skipped: Mapped[int | None] = mapped_column()
    num_deleted: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
