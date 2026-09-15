import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.core.schemas import ApiResponse, PaginatedData
from app.features.documents.v1.dependencies import get_document_service
from app.features.documents.v1.retriever.indexing_pipeline import (
    sync_github_repo_to_vectordb,
)
from app.features.documents.v1.schemas.req import IndexStatFilterParams
from app.features.documents.v1.schemas.res import (
    IndexStat,
)
from app.features.documents.v1.service import DocumentService

document_router = APIRouter()


@document_router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_rag_documents(background_tasks: BackgroundTasks):
    job_id = uuid.uuid4()
    background_tasks.add_task(sync_github_repo_to_vectordb, job_id)
    return ApiResponse(message="Sync job queued", data={"job_id": job_id})


@document_router.post("/stats", response_model=ApiResponse[PaginatedData[IndexStat]])
async def get_index_stats(
    filters: Annotated[IndexStatFilterParams, Query()],
    service: Annotated[
        DocumentService,
        Depends(get_document_service),
    ],
):
    paginated_index_stats = await service.get_index_stats(filters)
    return ApiResponse(data=paginated_index_stats)


@document_router.post("/stats/{job_id}", response_model=ApiResponse[IndexStat])
async def get_job_index_stats(
    job_id: uuid.UUID,
    service: Annotated[
        DocumentService,
        Depends(get_document_service),
    ],
):
    index_stats = await service.get_job_index_stats(job_id)
    return ApiResponse(data=index_stats)
