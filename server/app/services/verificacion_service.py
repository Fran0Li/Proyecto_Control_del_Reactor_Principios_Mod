"""Verificación del correo (US-02)."""

from datetime import timedelta

from app.core.config import settings
from app.core.security import generar_token
from app.models.usuario import Usuario
from app.repositories import UsuarioRepository
from app.services.correo import EnviadorCorreo
from app.services.tokens_correo import TokensDeCorreo

TIPO = "verificacion"
HORAS_VALIDEZ = 24


class VerificacionService:
    def __init__(
        self, usuarios: UsuarioRepository, tokens: TokensDeCorreo, enviador: EnviadorCorreo
    ) -> None:
        self.usuarios = usuarios
        self.tokens = tokens
        self.enviador = enviador

    def enviar_correo(self, usuario: Usuario) -> None:
        token = generar_token()
        self.tokens.guardar(usuario.id, TIPO, token, timedelta(hours=HORAS_VALIDEZ))
        enlace = f"{settings.url_publica}/auth/verificar?token={token}"
        self.enviador.enviar(
            usuario.correo,
            "Verificá tu cuenta de Control del Reactor",
            f"Hola {usuario.nombre_usuario}:\n\n"
            f"Para activar tu cuenta abrí este enlace:\n{enlace}\n\n"
            f"El enlace vence en {HORAS_VALIDEZ} horas. "
            "Si vos no creaste la cuenta, ignorá este correo.",
        )

    def verificar(self, token: str) -> Usuario:
        registro = self.tokens.usar(token, TIPO)
        usuario = self.usuarios.obtener_por_id(registro.usuario_id)
        usuario.correo_verificado = True
        return self.usuarios.guardar(usuario)

    def reenviar(self, correo: str) -> None:
        # misma respuesta exista o no la cuenta, para no revelar qué correos están registrados
        usuario = self.usuarios.obtener_por_correo(correo.strip().lower())
        if usuario is not None and not usuario.correo_verificado:
            self.enviar_correo(usuario)
