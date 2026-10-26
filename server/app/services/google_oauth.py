"""Comunicación con Google para el login (US-04), con OAuth 2.0."""

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import settings

URL_AUTORIZACION = "https://accounts.google.com/o/oauth2/v2/auth"
URL_TOKEN = "https://oauth2.googleapis.com/token"
URL_PERFIL = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleError(Exception):
    pass


@dataclass(frozen=True)
class PerfilGoogle:
    google_id: str
    correo: str
    correo_verificado: bool


class ProveedorGoogle:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    @property
    def configurado(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def url_autorizacion(self, estado: str) -> str:
        parametros = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email",
            "state": estado,
            "prompt": "select_account",
        }
        return f"{URL_AUTORIZACION}?{urlencode(parametros)}"

    def obtener_perfil(self, codigo: str) -> PerfilGoogle:
        """Cambia el código que manda Google por los datos de la cuenta."""
        try:
            respuesta = httpx.post(
                URL_TOKEN,
                data={
                    "code": codigo,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=10,
            )
            respuesta.raise_for_status()
            token = respuesta.json()["access_token"]

            respuesta = httpx.get(
                URL_PERFIL, headers={"Authorization": f"Bearer {token}"}, timeout=10
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
            return PerfilGoogle(
                google_id=str(datos["sub"]),
                correo=datos["email"].lower(),
                correo_verificado=bool(datos.get("email_verified")),
            )
        except (httpx.HTTPError, KeyError, ValueError) as error:
            raise GoogleError("No se pudo completar el login con Google") from error


def crear_proveedor_google() -> ProveedorGoogle:
    return ProveedorGoogle(
        settings.google_client_id,
        settings.google_client_secret,
        f"{settings.url_publica}/auth/google/callback",
    )
