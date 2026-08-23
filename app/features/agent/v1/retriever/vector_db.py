from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector

from app.core.config import settings
from app.core.database.session import async_engine

embedding_model = settings.embedding_model
vector_collection_name = settings.vector_collection_name


embeddings = HuggingFaceEmbeddings(model_name=embedding_model)

vector_store = PGVector(
    embeddings=embeddings,
    collection_name=vector_collection_name,
    connection=async_engine,
)


hybrid_retriever = vector_store.as_retriever(
    search_type="hybrid",
    search_kwargs={"k": 5},
)
