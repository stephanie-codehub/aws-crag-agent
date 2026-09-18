"""Utilities for indexing local and GitHub document sources into the vector database.

This module converts source documents into chunked LangChain documents, stores them in
an SQL-backed record manager, and updates the vector index while tracking job status.
"""

import gc
import io
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import httpx
import structlog
from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from langchain_classic.indexes import SQLRecordManager, index
from langchain_core.documents import Document
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.features.documents.v1.models import IndexStatRecord
from app.features.documents.v1.retriever.vector_db import vector_store
from app.features.documents.v1.schemas.enums import IndexingStatus

db_url = settings.sqlalchemy_database_url.get_secret_value().replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)

sync_engine = create_engine(
    db_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
)

logger = structlog.get_logger()
embedding_model = settings.embedding_model
vector_collection_name = settings.vector_collection_name
vector_db_type = settings.vector_db_type
RECORD_DB_PATH = settings.record_manager_db_path

tokenizer = HuggingFaceTokenizer.from_pretrained(embedding_model)
chunker = HybridChunker(tokenizer=tokenizer)
converter = DocumentConverter()


def sync_folder_to_vectordb(job_id: uuid.UUID) -> None:
    """Index all files from the configured local documents folder into the vector store.

    The function creates a job record, converts each supported file into chunks, pushes
    those chunks to the vector database with incremental cleanup, and updates the job
    status to completed or failed. Deleted local files are also removed from the index
    when they are no longer present in the configured folder.

    Args:
        job_id: Unique identifier for the indexing job tracked in the database.
    """
    record_manager = SQLRecordManager(
        namespace=f"{vector_db_type}/{vector_collection_name}", db_url=RECORD_DB_PATH
    )
    record_manager.create_schema()
    total_stats = {"num_added": 0, "num_updated": 0, "num_skipped": 0, "num_deleted": 0}
    active_sources: set[str] = set()
    documents_folder = settings.documents_folder

    with Session(sync_engine) as db:
        new_job = IndexStatRecord(
            job_id=job_id,
            start_time=datetime.now(UTC),
            status=IndexingStatus.PROCESSING,
            num_added=0,
            num_updated=0,
            num_skipped=0,
            num_deleted=0,
        )
        db.add(new_job)
        db.commit()

        try:
            folder = Path(documents_folder)
            if not folder.exists():
                new_job.status = IndexingStatus.COMPLETED
                new_job.stop_time = datetime.now(UTC)
                db.commit()
                return

            file_paths = [path for path in folder.iterdir() if path.is_file()]

            for file_path in file_paths:
                source_id = f"local:{file_path.name}"
                active_sources.add(source_id)

                result = converter.convert(file_path)
                chunks = chunker.chunk(result.document)
                document_chunks = []

                for chunk in chunks:
                    meta = chunk.meta.model_dump()
                    metadata = {
                        k: v
                        for k, v in meta.items()
                        if isinstance(v, (str, int, float, bool))
                    }
                    metadata["source"] = source_id

                    document_chunk = Document(
                        page_content=chunker.contextualize(chunk), metadata=metadata
                    )
                    document_chunks.append(document_chunk)

                if document_chunks:
                    stats = index(
                        document_chunks,
                        record_manager,
                        vector_store,
                        cleanup="incremental",
                        source_id_key="source",
                    )
                    for k in total_stats:
                        total_stats[k] += cast(int, stats.get(k, 0))

                del result
                del document_chunks
                gc.collect()

            # Identify deleted/stale local files
            all_tracked_keys = record_manager.list_keys(limit=10000)
            all_tracked_sources = {
                key.split(":")[0] for key in all_tracked_keys if ":" in key
            }

            for tracked_source in all_tracked_sources:
                if (
                    tracked_source.startswith("local:")
                    and tracked_source not in active_sources
                ):
                    # Pass a dummy document targeted at source_id to trigger cleanup for deleted file
                    dummy_doc = Document(
                        page_content="", metadata={"source": tracked_source}
                    )
                    deletion_stats = index(
                        [dummy_doc],
                        record_manager=record_manager,
                        vector_store=vector_store,
                        cleanup="incremental",
                        source_id_key="source",
                    )
                    total_stats["num_deleted"] += deletion_stats.get("num_deleted", 0)

            # Save metrics
            new_job.num_added = total_stats["num_added"]
            new_job.num_updated = total_stats["num_updated"]
            new_job.num_skipped = total_stats["num_skipped"]
            new_job.num_deleted = total_stats["num_deleted"]
            new_job.status = IndexingStatus.COMPLETED
            new_job.stop_time = datetime.now(UTC)
            db.commit()

        except Exception:
            db.rollback()
            job_record = db.query(IndexStatRecord).filter_by(job_id=job_id).first()
            if job_record:
                job_record.status = IndexingStatus.FAILED
                job_record.stop_time = datetime.now(UTC)
                db.commit()
            logger.exception(f"Background Job {job_id} failed")


def sync_github_repo_to_vectordb(job_id: uuid.UUID) -> None:
    """Index markdown and PDF files from the configured GitHub repository.

    The repository tree is inspected recursively, each matching blob is downloaded,
    converted into chunks, and inserted into the vector store. Any previously indexed
    GitHub source that is no longer present in the repo is cleaned up incrementally.

    Args:
        job_id: Unique identifier for the GitHub indexing job tracked in the database.
    """
    record_manager = SQLRecordManager(
        namespace=f"{vector_db_type}/{vector_collection_name}",
        db_url=RECORD_DB_PATH,
    )
    record_manager.create_schema()

    active_github_sources: set[str] = set()
    total_stats = {"num_added": 0, "num_updated": 0, "num_skipped": 0, "num_deleted": 0}

    gh_user = settings.documents_github_user.strip("/")
    gh_repo = settings.documents_github_repo.strip("/")
    gh_branch = settings.documents_github_branch

    with Session(sync_engine) as db:
        new_job = IndexStatRecord(
            job_id=job_id,
            start_time=datetime.now(UTC),
            status=IndexingStatus.PROCESSING,
            num_added=0,
            num_updated=0,
            num_skipped=0,
            num_deleted=0,
        )
        db.add(new_job)
        db.commit()

        try:
            with httpx.Client() as client:
                tree_url = f"https://github.com/{gh_user}/{gh_repo}/git/trees/{gh_branch}?recursive=1"
                repo_tree = client.get(tree_url).json()

                for item in repo_tree.get("tree", []):
                    file_path_str = item["path"]
                    file_name = file_path_str.split("/")[-1]

                    if item["type"] == "blob" and file_path_str.endswith(
                        (".md", ".pdf")
                    ):
                        source_id = f"github:{file_name}"
                        active_github_sources.add(source_id)

                        raw_url = f"https://githubusercontent.com/{gh_user}/{gh_repo}/{gh_branch}/{file_path_str}"
                        file_response = client.get(raw_url)

                        file_bytes = io.BytesIO(file_response.content)
                        doc_stream = DocumentStream(name=file_name, stream=file_bytes)

                        result = converter.convert(doc_stream)
                        chunks = chunker.chunk(result.document)
                        document_chunks = []

                        for chunk in chunks:
                            meta = chunk.meta.model_dump()
                            metadata = {
                                k: v
                                for k, v in meta.items()
                                if isinstance(v, (str, int, float, bool))
                            }
                            metadata["source"] = source_id
                            metadata["github_sha"] = item["sha"]

                            document_chunk = Document(
                                page_content=chunker.contextualize(chunk),
                                metadata=metadata,
                            )
                            document_chunks.append(document_chunk)

                        if document_chunks:
                            stats = index(
                                document_chunks,
                                record_manager,
                                vector_store,
                                cleanup="incremental",
                                source_id_key="source",
                            )
                            for k in total_stats:
                                total_stats[k] += cast(int, stats.get(k, 0))

                        del result
                        del document_chunks
                        gc.collect()

            # Handle deletion of removed GitHub files
            all_tracked_keys = record_manager.list_keys(limit=10000)
            all_tracked_sources = {
                key.split(":")[0] for key in all_tracked_keys if ":" in key
            }

            for tracked_source in all_tracked_sources:
                if (
                    tracked_source.startswith("github:")
                    and tracked_source not in active_github_sources
                ):
                    dummy_doc = Document(
                        page_content="", metadata={"source": tracked_source}
                    )
                    deletion_stats = index(
                        [dummy_doc],
                        record_manager=record_manager,
                        vector_store=vector_store,
                        cleanup="incremental",
                        source_id_key="source",
                    )
                    total_stats["num_deleted"] += deletion_stats.get("num_deleted", 0)

            new_job.num_added = total_stats["num_added"]
            new_job.num_updated = total_stats["num_updated"]
            new_job.num_skipped = total_stats["num_skipped"]
            new_job.num_deleted = total_stats["num_deleted"]
            new_job.status = IndexingStatus.COMPLETED
            new_job.stop_time = datetime.now(UTC)
            db.commit()

        except Exception:
            db.rollback()
            job_record = db.query(IndexStatRecord).filter_by(job_id=job_id).first()
            if job_record:
                job_record.status = IndexingStatus.FAILED
                job_record.stop_time = datetime.now(UTC)
                db.commit()
            logger.exception(f"Background GitHub Job {job_id} failed")
