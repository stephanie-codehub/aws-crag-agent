import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.documents.v1.models import IndexStatRecord


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_index_stats(
        self, filter_dict: dict
    ) -> tuple[list[IndexStatRecord], int]:
        query = select(IndexStatRecord)
        filter_dict_page = filter_dict["page"]
        filter_dict_size = filter_dict["size"]
        filters = []

        if filter_dict.get("status"):
            filters.append(IndexStatRecord.status.ilike(f"%{filter_dict['status']}%"))

        if filters:
            query = query.where(and_(*filters))

        count_query = select(func.count()).select_from(query.subquery())
        total_count_result = await self.session.execute(count_query)
        total_count = total_count_result.scalar_one()

        offset_value = (filter_dict_page - 1) * filter_dict_size
        paginated_query = query.offset(offset_value).limit(filter_dict_size)

        result = await self.session.execute(paginated_query)
        index_stats = list(result.scalars().all())

        return index_stats, total_count

    async def get_index_stat_by_id(self, job_id: uuid.UUID) -> IndexStatRecord | None:
        statement = select(IndexStatRecord).where(IndexStatRecord.job_id == job_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def save_index_stat_record(
        self, index_stat_model: IndexStatRecord
    ) -> IndexStatRecord:
        self.session.add(index_stat_model)
        await self.session.flush()
        return index_stat_model
