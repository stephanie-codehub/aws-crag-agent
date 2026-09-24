from llama_index.core import VectorStoreIndex
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from app.core.config import settings
from app.core.database.session import async_engine, sync_engine

embedding_model = settings.embedding_model
vector_collection_name = settings.vector_collection_name

embeddings = FastEmbedEmbedding(model_name=embedding_model)

vector_store = PGVectorStore(
    engine=sync_engine,
    async_engine=async_engine,
    table_name=vector_collection_name,
    embed_dim=384,
    hybrid_search=True,
)

index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embeddings)

hybrid_retriever = index.as_retriever(
    vector_store_query_mode="hybrid",
    similarity_top_k=5,
)
