import gc
import io
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
import structlog
from docling.chunking import HybridChunker
from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter
from langchain.indexes import SQLRecordManager, index
from langchain_core.documents import Document
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from transformers import AutoTokenizer

from app.core.config import settings
from app.features.documents.v1.models import IndexStatRecord
from app.features.documents.v1.retriever.vector_db import vector_store
from app.features.documents.v1.schemas.enums import IndexingStatus

db_url = settings.database_url.get_secret_value().replace(
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

tokenizer = AutoTokenizer.from_pretrained(embedding_model, use_fast=True)
chunker = HybridChunker(tokenizer=tokenizer)
converter = DocumentConverter()


def sync_folder_to_vectordb(job_id: uuid.UUID):
    record_manager = SQLRecordManager(
        namespace=f"{vector_db_type}/{vector_collection_name}", db_url=RECORD_DB_PATH
    )
    record_manager.create_schema()
    total_stats = {"num_added": 0, "num_updated": 0, "num_skipped": 0, "num_deleted": 0}
    active_sources = set()
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
                document_chunks = []
                active_sources.add(file_path.name)

                result = converter.convert(file_path)
                chunks = chunker.chunk(result.extracted_doc)

                for chunk in chunks:
                    meta = chunk.meta.model_dump()
                    metadata = {
                        k: v
                        for k, v in meta.items()
                        if isinstance(v, (str, int, float, bool))
                    }
                    metadata["source"] = file_path.name

                    document_chunk = Document(
                        page_content=chunker.serialize(chunk), metadata=metadata
                    )
                    document_chunks.append(document_chunk)

                if document_chunks:
                    stats = index(
                        document_chunks,
                        record_manager,
                        vector_store,
                        cleanup="scoped_full",
                        source_id_key="source",
                    )
                    for k in total_stats:
                        total_stats[k] += stats.get(k, 0)
                # free up memory
                del result
                del document_chunks
                gc.collect()

            all_tracked_keys = record_manager.list_keys(limit=10000)
            all_tracked_sources = {
                key.split(":")[0] for key in all_tracked_keys if ":" in key
            } or set()

            for tracked_source in all_tracked_sources:
                if tracked_source not in active_sources:
                    deletion_stats = index(
                        [],
                        record_manager=record_manager,
                        vector_store=vector_store,
                        cleanup="scoped_full",
                        source_id_key="source",
                        group_ids=[tracked_source],
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
            new_job.status = IndexingStatus.FAILED
            new_job.stop_time = datetime.now(UTC)
            db.commit()
            logger.exception(f"Background Job {job_id} failed")


def sync_github_repo_to_vectordb(job_id: uuid.UUID):
    record_manager = SQLRecordManager(
        namespace=f"{vector_db_type}/{vector_collection_name}",
        db_url=RECORD_DB_PATH,
    )
    record_manager.create_schema()

    active_github_sources = set()
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

                    if item["type"] == "blob" and (
                        file_path_str.endswith((".md", ".pdf"))
                    ):
                        active_github_sources.add(file_name)

                        raw_url = f"https://githubusercontent.com/{gh_user}/{gh_repo}/{gh_branch}/{file_path_str}"
                        file_response = client.get(raw_url)

                        file_bytes = io.BytesIO(file_response.content)
                        doc_stream = DocumentStream(name=file_name, stream=file_bytes)

                        document_chunks = []
                        result = converter.convert(doc_stream)
                        chunks = chunker.chunk(result.extracted_doc)

                        for chunk in chunks:
                            meta = chunk.meta.model_dump()
                            metadata = {
                                k: v
                                for k, v in meta.items()
                                if isinstance(v, (str, int, float, bool))
                            }
                            metadata["source"] = file_name
                            metadata["github_sha"] = item["sha"]

                            document_chunk = Document(
                                page_content=chunker.serialize(chunk), metadata=metadata
                            )
                            document_chunks.append(document_chunk)

                        if document_chunks:
                            stats = index(
                                document_chunks,
                                record_manager,
                                vector_store,
                                cleanup="scoped_full",
                                source_id_key="source",
                            )
                            for k in total_stats:
                                total_stats[k] += stats.get(k, 0)

                        del result
                        del document_chunks
                        gc.collect()

            all_tracked_keys = record_manager.list_keys(limit=10000)
            all_tracked_sources = {
                key.split(":")[0] for key in all_tracked_keys if ":" in key
            } or set()

            for tracked_source in all_tracked_sources:
                if tracked_source not in active_github_sources:
                    deletion_stats = index(
                        [],
                        record_manager=record_manager,
                        vector_store=vector_store,
                        cleanup="scoped_full",
                        source_id_key="source",
                        group_ids=[tracked_source],
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
            new_job.status = IndexingStatus.FAILED
            new_job.stop_time = datetime.now(UTC)
            db.commit()
            logger.exception(f"Background GitHub Job {job_id} failed")
