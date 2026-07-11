"""Configuración de la app: variables de entorno."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"

    # ID de la hoja de cálculo (el valor entre /d/ y /edit en la URL).
    google_sheet_id: str = ""

    # Credenciales de la cuenta de servicio de Google Cloud.
    # Opción A (recomendada en Render): pega el JSON completo en esta variable.
    # Opción B (desarrollo local): deja un archivo backend/credentials.json y
    # no definas esta variable; se usará ese archivo automáticamente.
    google_service_account_json: str = ""
    google_credentials_file: Path = BASE_DIR / "credentials.json"

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
