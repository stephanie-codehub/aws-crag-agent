from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_session
from app.features.documents.v1.repository import DocumentRepository
from app.features.documents.v1.service import DocumentService


def get_document_repo(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentRepository:
    return DocumentRepository(session=session)


def get_document_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
) -> DocumentService:
    return DocumentService(
        session=session,
        documents_repo=document_repo,
    )
