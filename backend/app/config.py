"""Configuración de la app: variables de entorno."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"

    # Connection string con pooler de Supabase (puerto 6543, modo
    # transacción/pgbouncer) — ver backend/db/schema.sql.
    database_url: str = ""

    # Opcional: habilita la búsqueda de canciones en YouTube al agregarlas.
    # Sin esta key, el buscador simplemente no se muestra en el frontend.
    youtube_api_key: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
