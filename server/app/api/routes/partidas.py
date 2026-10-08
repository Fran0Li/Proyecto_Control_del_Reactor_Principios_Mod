"""Endpoints de partidas (US-07)."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models.partida import EstadoPartida
from app.repositories import PartidaRepository, UsuarioRepository
from app.services.partida_service import JugadorYaEnPartidaError, PartidaService

router = APIRouter(prefix="/partidas", tags=["partidas"])
SessionDep = Annotated[Session, Depends(get_session)]


class CrearPartidaRequest(BaseModel):
    creador_id: int
    escenario: str | None = None


class PartidaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estado: EstadoPartida
    escenario: str
    tiempo_limite_segundos: int
    puntuacion_objetivo: int


@router.post("", response_model=PartidaResponse, status_code=status.HTTP_201_CREATED)
def crear_partida(datos: CrearPartidaRequest, db: SessionDep):
    if UsuarioRepository(db).obtener_por_id(datos.creador_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jugador no encontrado")

    servicio = PartidaService(PartidaRepository(db))
    try:
        return servicio.crear_partida(datos.creador_id, datos.escenario)
    except JugadorYaEnPartidaError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error