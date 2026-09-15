import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundException
from app.core.schemas import PaginatedData
from app.features.documents.v1.models import IndexStatRecord
from app.features.documents.v1.repository import DocumentRepository
from app.features.documents.v1.schemas.req import IndexStatFilterParams
from app.features.documents.v1.schemas.res import IndexStat


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        documents_repo: DocumentRepository,
    ):
        self.session = session
        self.documents_repo = documents_repo

    async def get_index_stats(
        self, filters: IndexStatFilterParams
    ) -> PaginatedData[IndexStat]:
        index_stats, total_count = await self.documents_repo.get_index_stats(
            filters.model_dump(exclude_unset=True)
        )
        index_stat_schemas = [
            IndexStat.model_validate(index_stat) for index_stat in index_stats
        ]

        paginated_index_stats = PaginatedData(
            items=index_stat_schemas,
            total=total_count,
            page=filters.page,
            size=filters.size,
        )
        return paginated_index_stats

    async def get_job_index_stats(self, job_id: uuid.UUID) -> IndexStatRecord:
        index_stat = await self.documents_repo.get_index_stat_by_id(job_id)
        if not index_stat:
            raise ResourceNotFoundException()
        return index_stat
