"""Configuración leída de variables de entorno (archivo .env)."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://reactor:reactor_dev@localhost:5432/reactor"
    )
    # HS256 pide una clave de al menos 32 bytes; esta es solo para desarrollo y pruebas.
    jwt_secret: str = os.getenv("JWT_SECRET", "solo-desarrollo-cambiar-en-produccion-32+")
    # Orígenes web que pueden llamar a la API (cliente móvil con pygbag). "*" = cualquiera, solo
    # para desarrollo; en la nube poner el dominio del cliente, separados por coma.
    cors_origenes: str = os.getenv("CORS_ORIGENES", "*")
    # Dirección con la que se arman los enlaces de los correos
    url_publica: str = os.getenv("URL_PUBLICA", "http://localhost:8000")
    # Sin SMTP_HOST los correos se muestran en la consola del servidor (para desarrollo)
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT") or 587)
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    # Login con Google (US-04). Cómo crearlas: docs/google-oauth.md
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")


settings = Settings()
