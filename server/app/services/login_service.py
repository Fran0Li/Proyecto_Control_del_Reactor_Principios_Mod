"""Inicio de sesión (US-03)."""

from app.core.security import PasswordHasher, ScryptPasswordHasher, crear_token_acceso
from app.models.usuario import Usuario
from app.repositories import UsuarioRepository


class LoginError(Exception):
    pass


class CredencialesInvalidasError(LoginError):
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

        if not self.hasher.verificar(contrasena, usuario.contrasena_hash):
            raise CredencialesInvalidasError("Usuario o contraseña incorrectos")

        # se revisa después de la contraseña para no revelar qué cuentas existen
        if not usuario.correo_verificado:
            raise CorreoNoVerificadoError("Verificá tu correo antes de iniciar sesión")

        return usuario, crear_token_acceso(usuario.id)
