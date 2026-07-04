"""Environment-driven configuration. No hardcoded secrets or project IDs."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    bq_project_id: str = Field(default="dev-project", validation_alias="BQ_PROJECT_ID")
    bq_dataset: str = Field(default="analytics", validation_alias="BQ_DATASET")
    max_bytes_billed: int = Field(default=1_000_000_000, validation_alias="MAX_BYTES_BILLED")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    agent_step_cap: int = Field(default=10, validation_alias="AGENT_STEP_CAP")
    token_budget: int = Field(default=8000, validation_alias="TOKEN_BUDGET")


@lru_cache
def get_settings() -> Settings:
    return Settings()
