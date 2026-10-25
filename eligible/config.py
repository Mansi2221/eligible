"""Central configuration, loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # DeepSeek (OpenAI-compatible)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model_flash: str = "deepseek-v4-flash"
    deepseek_model_pro: str = "deepseek-v4-pro"

    # Postgres (OMOP store)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "eligible"
    postgres_user: str = "eligible"
    postgres_password: str = "eligible"

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index: str = "eligible-criteria"

    # Auth / audit
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    audit_log_path: str = "data/audit_log.jsonl"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
