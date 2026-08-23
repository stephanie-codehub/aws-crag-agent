from pathlib import Path

from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from langchain_classic.indexes import SQLRecordManager, index
from langchain_docling import DoclingLoader
from transformers import AutoTokenizer

from app.core.config import settings
from app.features.agent.v1.retriever.vector_db import vector_store

embedding_model = settings.embedding_model
documents_folder = settings.documents_folder
vector_collection_name = settings.vector_collection_name
vector_db_type = settings.vector_db_type
RECORD_DB_PATH = settings.record_manager_db_path


def get_document_chunks():
    folder = Path(documents_folder)
    file_names = [str(path) for path in folder.iterdir() if path.is_file()]

    tokenizer = AutoTokenizer.from_pretrained(embedding_model, use_fast=True)

    loader = DoclingLoader(
        file_path=file_names,
        chunker=HybridChunker(tokenizer=tokenizer),
    )
    documents = loader.lazy_load()

    for document in documents:
        # Remove nested lists/dicts for Pinecone metadata storage
        document.metadata = {
            k: v
            for k, v in document.metadata.items()
            if isinstance(v, (str, int, float, bool))
        }
    return documents


def sync_folder_to_vectordb():
    record_manager = SQLRecordManager(
        namespace=f"{vector_db_type}/{vector_collection_name}", db_url=RECORD_DB_PATH
    )
    record_manager.create_schema()

    document_chunks = get_document_chunks()

    # Incremental indexing
    stats = index(
        document_chunks,
        record_manager,
        vector_store,
        cleanup="full",
        source_id_key="source",
    )

    return stats
