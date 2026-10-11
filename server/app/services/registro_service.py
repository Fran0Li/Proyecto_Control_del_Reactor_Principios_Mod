"""Servicio de registro de usuarios (US-01).

Reglas que aplica:
- RN-01: un correo solo puede pertenecer a un jugador.
- El nombre de usuario es único.
- La contraseña se guarda hasheada (RNF-03).
- La cuenta nace pendiente de verificación; US-02 la marca como verificada.
"""

from sqlalchemy.exc import IntegrityError

from app.core.security import PasswordHasher, ScryptPasswordHasher
from app.models.usuario import Usuario
from app.repositories import UsuarioRepository


class RegistroError(Exception):
    """No se pudo registrar al usuario porque sus datos chocan con otra cuenta."""


class NombreUsuarioDuplicadoError(RegistroError):
    """Ya existe una cuenta con ese nombre de usuario."""


class CorreoDuplicadoError(RegistroError):
    """RN-01: ya existe una cuenta con ese correo."""


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
            correo_verificado=False,
            contrasena_hash=self.hasher.hash(contrasena),
        )
        try:
            return self.repo.crear(usuario)
        except IntegrityError as error:
            # Dos registros simultáneos con los mismos datos: la restricción UNIQUE
            # de la base de datos detiene al segundo.
            raise RegistroError("El nombre de usuario o el correo ya están registrados") from error
