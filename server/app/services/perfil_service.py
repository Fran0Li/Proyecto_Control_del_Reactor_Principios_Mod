"""Consultar y editar el perfil del jugador (US-06)."""

from typing import Literal, get_args

from sqlalchemy.exc import IntegrityError

from app.models.usuario import Usuario
from app.repositories import UsuarioRepository

Avatar = Literal["azul", "verde", "naranja", "morado", "rojo"]
AVATARES = get_args(Avatar)


class NombreEnUsoError(Exception):
    pass


class PerfilService:
    def __init__(self, usuarios: UsuarioRepository) -> None:
        self.usuarios = usuarios

    def ver(self, usuario: Usuario) -> dict:
        return {
            "id": usuario.id,
            "nombre_usuario": usuario.nombre_usuario,
            "correo": usuario.correo,
            "descripcion": usuario.descripcion or "",
            "avatar": usuario.avatar or AVATARES[0],
            "fecha_registro": usuario.fecha_registro,
            "con_google": usuario.google_id is not None,
            **self.usuarios.estadisticas(usuario.id),
        }

    def editar(
        self,
        usuario: Usuario,
        nombre_usuario: str | None = None,
        descripcion: str | None = None,
        avatar: str | None = None,
    ) -> dict:
        if nombre_usuario is not None and nombre_usuario != usuario.nombre_usuario:
            if self.usuarios.existe_nombre_usuario(nombre_usuario):
                raise NombreEnUsoError("El nombre de usuario ya está en uso")
            usuario.nombre_usuario = nombre_usuario
        if descripcion is not None:
            usuario.descripcion = descripcion.strip()
        if avatar is not None:
            usuario.avatar = avatar

        try:
            self.usuarios.guardar(usuario)
        except IntegrityError as error:
            # otro jugador tomó el mismo nombre al mismo tiempo
            raise NombreEnUsoError("El nombre de usuario ya está en uso") from error
        return self.ver(usuario)
