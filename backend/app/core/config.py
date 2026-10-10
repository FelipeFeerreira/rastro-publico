"""Configuração central da aplicação, carregada por variáveis de ambiente.

Todas as credenciais permanecem no servidor. Nada sensível é exposto ao cliente.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Aplicação ---
    app_name: str = "Rastro Público"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    # --- Banco de dados ---
    database_url: str = "postgresql+psycopg://rastro:rastro@localhost:5432/rastro_publico"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"
    enable_celery: bool = False

    # --- Segurança ---
    secret_key: str = "troque-esta-chave-em-producao"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    jwt_algorithm: str = "HS256"
    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 120
    rate_limit_search_per_minute: int = 40

    # --- Conectores ---
    pncp_base_url: str = "https://pncp.gov.br/api/consulta"
    pncp_page_size: int = 50
    pncp_timeout_seconds: int = 30
    pncp_max_retries: int = 4
    transparencia_api_key: str = ""
    transparencia_base_url: str = "https://api.portaldatransparencia.gov.br/api-de-dados"
    camara_base_url: str = "https://dadosabertos.camara.leg.br/api/v2"

    # --- IA (opcional) ---
    ai_provider: Literal["disabled", "openai", "local"] = "disabled"
    ai_model: str = ""
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_max_output_tokens: int = 1200

    # --- Armazenamento ---
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "rastro-documentos"
    s3_region: str = "us-east-1"

    @field_validator("cors_origins")
    @classmethod
    def _strip_origins(cls, value: str) -> str:
        return value.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def ai_enabled(self) -> bool:
        return self.ai_provider != "disabled" and bool(self.ai_api_key or self.ai_base_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
