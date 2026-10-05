"""Configuración leída de variables de entorno (archivo .env)."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://reactor:reactor_dev@localhost:5432/reactor"
    )
    jwt_secret: str = os.getenv("JWT_SECRET", "cambiar-esto-en-produccion")


settings = Settings()
