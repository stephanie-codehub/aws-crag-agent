"""Utilities for indexing local and GitHub document sources into the vector database.

This module converts source documents into chunked LangChain documents, stores them in
an SQL-backed record manager, and updates the vector index while tracking job status.
"""

import io
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
import structlog
from llama_index.core import Document as LlamaDocument
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.storage.docstore.postgres import PostgresDocumentStore
from markitdown import MarkItDown
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database.session import sync_engine
from app.features.documents.v1.models import IndexStatRecord
from app.features.documents.v1.retriever.vector_db import vector_store
from app.features.documents.v1.schemas.enums import IndexingStatus

db_url = settings.sync_database_url.get_secret_value()

TEXT_EXTENSIONS = {".md", ".txt", ".markdown", ".csv"}
logger = structlog.get_logger()
embedding_model = settings.embedding_model
vector_collection_name = settings.vector_collection_name
vector_db_type = settings.vector_db_type


header_splitter = MarkdownNodeParser()
text_splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=150)


embeddings = FastEmbedEmbedding(model_name=embedding_model)
markitdown = MarkItDown()

from llama_index.storage.kvstore.postgres import PostgresKVStore

# 1. Instantiate the underlying KV store directly
kv_store = PostgresKVStore.from_uri(
    uri=db_url,
    table_name="ingestion_store",
)

# 2. Pass the kv_store instance into PostgresDocumentStore
docstore = PostgresDocumentStore(postgres_kvstore=kv_store)

pipeline = IngestionPipeline(
    transformations=[header_splitter, text_splitter, embeddings],
    vector_store=vector_store,
    docstore=docstore,
)


def sync_folder_to_vectordb(job_id: uuid.UUID) -> None:
    """Index all files from the configured local documents folder into the vector store.

    The function creates a job record, converts each supported file into chunks, pushes
    those chunks to the vector database with incremental cleanup, and updates the job
    status to completed or failed. Deleted local files are also removed from the index
    when they are no longer present in the configured folder.

    Args:
        job_id: Unique identifier for the indexing job tracked in the database.
    """

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
                source_id = file_path.name
                active_sources.add(source_id)
                file_extension = file_path.suffix

                if file_extension in TEXT_EXTENSIONS:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        text_content = f.read()
                else:
                    result = markitdown.convert(file_path)
                    text_content = result.text_content

                base_doc = LlamaDocument(
                    text=text_content,
                    doc_id=source_id,
                    extra_info={"source": source_id},
                )

                existing_hash = docstore.get_document_hash(source_id)
                pipeline.run(documents=[base_doc])

                if existing_hash is None:
                    total_stats["num_added"] += 1
                elif existing_hash != base_doc.hash:
                    total_stats["num_updated"] += 1
                else:
                    total_stats["num_skipped"] += 1

            # Clean up deleted files
            all_tracked_docs = docstore.get_all_document_hashes()
            for document_hash, file_name in list(all_tracked_docs.items()):
                if file_name not in active_sources:
                    vector_store.delete(ref_doc_id=document_hash)
                    docstore.delete_document(doc_id=document_hash)
                    total_stats["num_deleted"] += 1

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
                    file_extension = (
                        f".{file_name.split('.')[-1]}" if "." in file_name else ""
                    )

                    if item["type"] == "blob" and file_path_str.endswith(
                        (".md", ".pdf")
                    ):
                        source_id = f"github:{file_name}"
                        active_github_sources.add(source_id)

                        raw_url = f"https://githubusercontent.com/{gh_user}/{gh_repo}/{gh_branch}/{file_path_str}"
                        file_response = client.get(raw_url)

                        file_bytes = io.BytesIO(file_response.content)

                        text_content = markitdown.convert_stream(
                            file_bytes, file_extension=file_extension
                        ).text_content

                        base_doc = LlamaDocument(
                            text=text_content,
                            doc_id=source_id,
                            extra_info={"source": source_id, "github_sha": item["sha"]},
                        )

                        existing_hash = docstore.get_document_hash(source_id)
                        pipeline.run(documents=[base_doc])

                        if existing_hash is None:
                            total_stats["num_added"] += 1
                        elif existing_hash != base_doc.hash:
                            total_stats["num_updated"] += 1
                        else:
                            total_stats["num_skipped"] += 1

            # Clean up deleted files
            all_tracked_docs = docstore.get_all_document_hashes()
            for document_hash, file_name in list(all_tracked_docs.items()):
                if file_name not in active_github_sources:
                    vector_store.delete(ref_doc_id=document_hash)
                    docstore.delete_document(doc_id=document_hash)
                    total_stats["num_deleted"] += 1

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
