"""Ranking global (US-19) e historial del jugador conectado (US-20)."""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.dependencias import SessionDep, UsuarioActual
from app.repositories import LogroRepository, PartidaRepository, RankingRepository
from app.services.ranking_service import HistorialService, RankingService

router = APIRouter(tags=["ranking"])


class FilaRankingResponse(BaseModel):
    posicion: int
    jugador_id: int
    nombre: str | None
    puntos_totales: int
    victorias: int


class RankingResponse(BaseModel):
    top: list[FilaRankingResponse]
    yo: FilaRankingResponse | None  # el puesto del jugador aunque no esté en el top


class ResumenResponse(BaseModel):
    partidas_jugadas: int
    victorias: int
    puntos_totales: int
    mejor_puntaje: int
    logros: int


class PartidaJugadaResponse(BaseModel):
    partida_id: int
    fecha: datetime | None
    escenario: str | None
    puntaje: int
    posicion: int | None
    jugadores: int
    gano: bool


class HistorialResponse(BaseModel):
    resumen: ResumenResponse
    partidas: list[PartidaJugadaResponse]


@router.get("/ranking", response_model=RankingResponse)
def ranking_global(usuario: UsuarioActual, db: SessionDep):
    return RankingService(RankingRepository(db)).ranking_global(usuario.id)


@router.get("/historial", response_model=HistorialResponse)
def historial(usuario: UsuarioActual, db: SessionDep):
    """Solo las partidas del jugador autenticado."""
    servicio = HistorialService(PartidaRepository(db), RankingRepository(db), LogroRepository(db))
    return servicio.historial(usuario.id)
