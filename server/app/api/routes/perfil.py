"""Perfil del jugador conectado (US-06)."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencias import SessionDep, UsuarioActual
from app.repositories import UsuarioRepository
from app.services.perfil_service import Avatar, NombreEnUsoError, PerfilService

router = APIRouter(prefix="/perfil", tags=["perfil"])


class PerfilResponse(BaseModel):
    id: int
    nombre_usuario: str
    correo: str
    descripcion: str
    avatar: str
    fecha_registro: datetime | None
    con_google: bool
    partidas_jugadas: int
    victorias: int
    puntos_totales: int


class EditarPerfilRequest(BaseModel):
    # todo es opcional: solo se cambia lo que venga
    nombre_usuario: str | None = Field(
        None, min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$"
    )
    descripcion: str | None = Field(None, max_length=200)
    avatar: Avatar | None = None


@router.get("", response_model=PerfilResponse)
def ver_perfil(usuario: UsuarioActual, db: SessionDep):
    return PerfilService(UsuarioRepository(db)).ver(usuario)


@router.patch("", response_model=PerfilResponse)
def editar_perfil(datos: EditarPerfilRequest, usuario: UsuarioActual, db: SessionDep):
    try:
        return PerfilService(UsuarioRepository(db)).editar(
            usuario, datos.nombre_usuario, datos.descripcion, datos.avatar
        )
    except NombreEnUsoError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
