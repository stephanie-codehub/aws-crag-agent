from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_postgres import PGVector

from app.core.config import settings
from app.core.database.session import async_engine, sync_engine

embedding_model = settings.embedding_model
vector_collection_name = settings.vector_collection_name

embeddings = FastEmbedEmbeddings(model_name=embedding_model)


async_vector_store = PGVector(
    embeddings=embeddings,
    collection_name=vector_collection_name,
    connection=async_engine,
)

sync_vector_store = PGVector(
    embeddings=embeddings,
    collection_name=vector_collection_name,
    connection=sync_engine,
)
