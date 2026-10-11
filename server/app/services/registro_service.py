"""Registro de usuarios (US-01)."""

from sqlalchemy.exc import IntegrityError

from app.core.security import PasswordHasher, ScryptPasswordHasher
from app.models.usuario import Usuario
from app.repositories import UsuarioRepository


class RegistroError(Exception):
    pass


class NombreUsuarioDuplicadoError(RegistroError):
    pass


class CorreoDuplicadoError(RegistroError):
    """RN-01: un correo solo puede ser de un jugador."""


class RegistroService:
    def __init__(self, repo: UsuarioRepository, hasher: PasswordHasher | None = None) -> None:
        self.repo = repo
        self.hasher = hasher or ScryptPasswordHasher()

    def registrar(self, nombre_usuario: str, correo: str, contrasena: str) -> Usuario:
        nombre_usuario = nombre_usuario.strip()
        correo = correo.strip().lower()

        if self.repo.existe_nombre_usuario(nombre_usuario):
            raise NombreUsuarioDuplicadoError("El nombre de usuario ya está en uso")
        if self.repo.existe_correo(correo):
            raise CorreoDuplicadoError("El correo ya está registrado")

        usuario = Usuario(
            nombre_usuario=nombre_usuario,
            correo=correo,
            correo_verificado=False,  # se verifica en US-02
            contrasena_hash=self.hasher.hash(contrasena),
        )
        try:
            return self.repo.crear(usuario)
        except IntegrityError as error:
            # por si dos personas se registran al mismo tiempo con el mismo correo
            raise RegistroError("El nombre de usuario o el correo ya están registrados") from error
