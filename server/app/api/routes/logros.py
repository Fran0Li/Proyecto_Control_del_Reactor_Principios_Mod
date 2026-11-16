"""Logros del jugador conectado (US-27). Lo usa el historial (US-20) para mostrarlos."""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.dependencias import SessionDep, UsuarioActual
from app.realtime.logros import CATALOGO
from app.repositories import LogroRepository

router = APIRouter(prefix="/logros", tags=["logros"])


class LogroResponse(BaseModel):
    clave: str
    nombre: str
    descripcion: str
    obtenido: bool
    obtenido_en: datetime | None
    partida_id: int | None


@router.get("", response_model=list[LogroResponse])
def mis_logros(usuario: UsuarioActual, db: SessionDep):
    """Todo el catálogo, marcando cuáles ya desbloqueó el jugador y en qué partida."""
    obtenidos = {fila.logro: fila for fila in LogroRepository(db).de_jugador(usuario.id)}
    return [
        LogroResponse(
            clave=logro.clave,
            nombre=logro.nombre,
            descripcion=logro.descripcion,
            obtenido=logro.clave in obtenidos,
            obtenido_en=obtenidos[logro.clave].obtenido_en if logro.clave in obtenidos else None,
            partida_id=obtenidos[logro.clave].partida_id if logro.clave in obtenidos else None,
        )
        for logro in CATALOGO
    ]
