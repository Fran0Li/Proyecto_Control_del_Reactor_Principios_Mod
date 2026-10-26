"""Inicio de sesión (US-03)."""

import math
from datetime import datetime, timedelta

from app.core.security import PasswordHasher, ScryptPasswordHasher, crear_token_acceso
from app.core.tiempo import ahora_utc
from app.models.usuario import Usuario
from app.repositories import UsuarioRepository

MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 15


class LoginError(Exception):
    pass


class CredencialesInvalidasError(LoginError):
    pass


class CuentaBloqueadaError(LoginError):
    pass


class CorreoNoVerificadoError(LoginError):
    pass


class LoginService:
    def __init__(self, repo: UsuarioRepository, hasher: PasswordHasher | None = None) -> None:
        self.repo = repo
        self.hasher = hasher or ScryptPasswordHasher()

    def iniciar_sesion(self, usuario_o_correo: str, contrasena: str) -> tuple[Usuario, str]:
        usuario = self.repo.obtener_por_nombre_o_correo(usuario_o_correo.strip())
        if usuario is None:
            raise CredencialesInvalidasError("Usuario o contraseña incorrectos")

        ahora = ahora_utc()
        if usuario.bloqueado_hasta and usuario.bloqueado_hasta > ahora:
            raise CuentaBloqueadaError(self._mensaje_bloqueo(usuario.bloqueado_hasta, ahora))

        if not self.hasher.verificar(contrasena, usuario.contrasena_hash):
            if self._registrar_fallo(usuario, ahora):
                raise CuentaBloqueadaError(self._mensaje_bloqueo(usuario.bloqueado_hasta, ahora))
            raise CredencialesInvalidasError("Usuario o contraseña incorrectos")

        # se revisa después de la contraseña para no revelar qué cuentas existen
        if not usuario.correo_verificado:
            raise CorreoNoVerificadoError("Verificá tu correo antes de iniciar sesión")

        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        self.repo.guardar(usuario)
        return usuario, crear_token_acceso(usuario.id, usuario.version_sesion)

    def _registrar_fallo(self, usuario: Usuario, ahora: datetime) -> bool:
        """Suma un intento fallido. Devuelve True si con este la cuenta quedó bloqueada."""
        usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1
        bloqueada = usuario.intentos_fallidos >= MAX_INTENTOS
        if bloqueada:
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = ahora + timedelta(minutes=MINUTOS_BLOQUEO)
        self.repo.guardar(usuario)
        return bloqueada

    def _mensaje_bloqueo(self, hasta: datetime, ahora: datetime) -> str:
        minutos = math.ceil((hasta - ahora).total_seconds() / 60)
        return f"Demasiados intentos fallidos. Probá de nuevo en {minutos} min"
