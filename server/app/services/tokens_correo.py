"""Crear y usar los tokens que se mandan por correo (US-02 y US-05)."""

from datetime import timedelta

from app.core.security import hash_token
from app.core.tiempo import ahora_utc
from app.models.token_usuario import TokenUsuario
from app.repositories import TokenRepository


class TokenNoValidoError(Exception):
    pass


class TokenVencidoError(TokenNoValidoError):
    pass


class TokensDeCorreo:
    def __init__(self, repo: TokenRepository) -> None:
        self.repo = repo

    def guardar(self, usuario_id: int, tipo: str, token: str, duracion: timedelta) -> None:
        """Guarda un token nuevo; los que el usuario tenía pendientes dejan de servir."""
        ahora = ahora_utc()
        self.repo.invalidar_pendientes(usuario_id, tipo, ahora)
        self.repo.crear(
            TokenUsuario(
                usuario_id=usuario_id,
                tipo=tipo,
                token_hash=hash_token(token),
                expira_en=ahora + duracion,
            )
        )

    def usar(self, token: str, tipo: str) -> TokenUsuario:
        """Marca el token como usado (sin guardar todavía) y lo devuelve."""
        registro = self.repo.buscar(hash_token(token.strip()), tipo)
        if registro is None or registro.usado_en is not None:
            raise TokenNoValidoError()
        ahora = ahora_utc()
        if registro.expira_en < ahora:
            raise TokenVencidoError()
        registro.usado_en = ahora
        return registro
