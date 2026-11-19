"""Endpoints de partidas (US-07)."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.dependencias import UsuarioActual
from app.db.session import get_session
from app.models.partida import EstadoPartida
from app.realtime.gestor_motores import gestor_motores
from app.repositories import PartidaRepository, UsuarioRepository
from app.services.partida_service import (
    FaltanJugadoresError,
    JugadorYaEnPartidaError,
    NoEsCreadorError,
    PartidaLlenaError,
    PartidaNoDisponibleError,
    PartidaNoEncontradaError,
    PartidaService,
)

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

class PartidaDisponibleResponse(BaseModel):
    id: int
    escenario: str
    jugadores: int
    tiempo_limite_segundos: int
    puntuacion_objetivo: int


@router.get("", response_model=list[PartidaDisponibleResponse])
def listar_partidas_disponibles(db: SessionDep):
    servicio = PartidaService(PartidaRepository(db))
    return [
        PartidaDisponibleResponse(
            id=partida.id,
            escenario=partida.escenario,
            jugadores=jugadores,
            tiempo_limite_segundos=partida.tiempo_limite_segundos,
            puntuacion_objetivo=partida.puntuacion_objetivo,
        )
        for partida, jugadores in servicio.listar_disponibles()
    ]

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



class UnirsePartidaRequest(BaseModel):
    jugador_id: int


@router.post("/{partida_id}/unirse", response_model=PartidaDisponibleResponse)
def unirse_a_partida(partida_id: int, datos: UnirsePartidaRequest, db: SessionDep):
    if UsuarioRepository(db).obtener_por_id(datos.jugador_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jugador no encontrado")

    servicio = PartidaService(PartidaRepository(db))
    try:
        partida, jugadores = servicio.unirse_a_partida(partida_id, datos.jugador_id)
    except PartidaNoEncontradaError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except (
        JugadorYaEnPartidaError,
        PartidaNoDisponibleError,
        PartidaLlenaError,
    ) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    return PartidaDisponibleResponse(
        id=partida.id,
        escenario=partida.escenario,
        jugadores=jugadores,
        tiempo_limite_segundos=partida.tiempo_limite_segundos,
        puntuacion_objetivo=partida.puntuacion_objetivo,
    )


@router.post("/{partida_id}/iniciar", response_model=PartidaResponse)
async def iniciar_partida(partida_id: int, usuario: UsuarioActual, db: SessionDep):
    """El creador arranca la partida: corre el reloj y los jugadores pasan a la arena (US-17)."""
    servicio = PartidaService(PartidaRepository(db))
    try:
        # la base es sincrónica: en otro hilo para no frenar los motores que están corriendo
        partida = await run_in_threadpool(servicio.iniciar_partida, partida_id, usuario.id)
    except PartidaNoEncontradaError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except NoEsCreadorError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    except (PartidaNoDisponibleError, FaltanJugadoresError) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    motor = gestor_motores.obtener(partida_id)
    motor.iniciar_partida(partida.tiempo_limite_segundos, partida.puntuacion_objetivo)
    return partida
