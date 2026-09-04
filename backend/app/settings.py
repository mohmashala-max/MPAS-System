from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "M-PAS Platform API"
    jwt_secret: str = "development-only-change-me-32-bytes"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    mpas_environment: str = "development"
    dev_username: str = "demo"
    dev_password: str = "change-me"
    dev_accounts_json: str = '{"demo":{"password":"change-me","role":"facility_manager","tenant_id":"tenant-demo","facilities":["*"]}}'
    alert_database_path: str = "mpas-alerts.db"
    image_storage_path: str = "mpas-images"
    max_image_bytes: int = 10_000_000

    model_config = SettingsConfigDict(env_prefix="MPAS_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
