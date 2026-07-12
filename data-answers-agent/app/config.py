"""Environment-driven configuration. No hardcoded secrets or project IDs."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    frontier_provider: Literal["nim", "anthropic"] = Field(
        default="nim",
        validation_alias="FRONTIER_PROVIDER",
    )
    frontier_model: str = Field(
        default="claude-sonnet-4-6",
        validation_alias="FRONTIER_MODEL",
    )
    nim_api_key: str = Field(default="", validation_alias="NIM_API_KEY")
    nim_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        validation_alias="NIM_BASE_URL",
    )
    nim_model: str = Field(
        default="meta/llama-3.3-70b-instruct",
        validation_alias="NIM_MODEL",
    )
    bq_project_id: str = Field(default="dev-project", validation_alias="BQ_PROJECT_ID")
    bq_dataset: str = Field(default="analytics", validation_alias="BQ_DATASET")
    max_bytes_billed: int = Field(default=1_000_000_000, validation_alias="MAX_BYTES_BILLED")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    agent_step_cap: int = Field(default=10, validation_alias="AGENT_STEP_CAP")
    token_budget: int = Field(default=8000, validation_alias="TOKEN_BUDGET")
    grounding_retrieval: Literal["keyword", "embedding", "auto"] = Field(
        default="auto",
        validation_alias="GROUNDING_RETRIEVAL",
    )
    embedding_match_threshold: float = Field(
        default=0.25,
        validation_alias="EMBEDDING_MATCH_THRESHOLD",
    )
    embedding_ambiguity_margin: float = Field(
        default=0.05,
        validation_alias="EMBEDDING_AMBIGUITY_MARGIN",
    )
    identity_mode: Literal["stub", "wif"] = Field(
        default="stub",
        validation_alias="IDENTITY_MODE",
    )
    bq_dev_service_account: str = Field(
        default="",
        validation_alias="BQ_DEV_SERVICE_ACCOUNT",
    )
    bq_impersonate_target: str = Field(
        default="",
        validation_alias="BQ_IMPERSONATE_TARGET",
    )
    wif_provider_config: str = Field(
        default="",
        validation_alias="WIF_PROVIDER_CONFIG",
    )
    cors_origins: str = Field(
        default="http://localhost:3000",
        validation_alias="CORS_ORIGINS",
    )
    warehouse_backend: Literal["mock", "bigquery", "postgres"] = Field(
        default="mock",
        validation_alias="WAREHOUSE_BACKEND",
    )
    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    use_mcp_transport: bool = Field(default=False, validation_alias="USE_MCP")
    mcp_python: str = Field(default="", validation_alias="MCP_PYTHON")
    classify_provider: Literal["auto", "heuristic", "nim"] = Field(
        default="auto",
        validation_alias="CLASSIFY_PROVIDER",
    )
    upstash_redis_rest_url: str = Field(
        default="",
        validation_alias="UPSTASH_REDIS_REST_URL",
    )
    upstash_redis_rest_token: str = Field(
        default="",
        validation_alias="UPSTASH_REDIS_REST_TOKEN",
    )
    audit_store_backend: Literal["memory", "redis", "auto"] = Field(
        default="auto",
        validation_alias="AUDIT_STORE_BACKEND",
    )
    audit_redis_ttl_seconds: int = Field(
        default=604_800,
        validation_alias="AUDIT_REDIS_TTL_SECONDS",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
