from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./dados.db"
    secret_key: str = ""
    jwt_expira_minutos: int = 60
    bcb_timeout_segundos: float = 10.0
    upload_max_bytes: int = 5 * 1024 * 1024
    importacao_max_linhas: int = 20_000


@lru_cache
def get_settings() -> Settings:
    return Settings()
