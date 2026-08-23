import os
from pathlib import Path

from pydantic import DirectoryPath, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class AppSettings(BaseSettings):
    api_name: str = "AWS EC2 C-RAG Agent"
    api_version: str = "v1.0.0"
    api_log_level: str = "INFO"
    allowed_hosts: list[str] = ["*"]
    allowed_origins: list[str] = ["*"]

    database_url: SecretStr

    groq_api_key: SecretStr
    prompts_dir: DirectoryPath = Field(
        default_factory=lambda: BASE_DIR / "features" / "agent" / "v1" / "prompts"
    )

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    documents_folder: str = "knowledge_base"
    vector_collection_name: str = "aws_ec2_documentation"
    vector_db_type: str = "pgvector"
    record_manager_db_path: str = "sqlite:///vectordb/record_manager_cache.sql"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = AppSettings()  # type: ignore
os.environ["GROQ_API_KEY"] = settings.groq_api_key.get_secret_value()
