from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GujRERA Gateway"
    app_env: Literal["development", "production"] = "production"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    gujrera_base_url: str = "https://gujrera.gujarat.gov.in"
    gujrera_timeout_connect: float = 10.0
    gujrera_timeout_read: float = 30.0
    gujrera_max_connections: int = 30
    gujrera_max_keepalive_connections: int = 15

    listing_cache_ttl_seconds: int = 3600
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])
    local_db_path: str = str(Path("data") / "gujrera_local.db")
    local_sync_concurrency: int = 4
    local_sync_batch_size: int = 100
    rag_default_limit: int = 8

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
