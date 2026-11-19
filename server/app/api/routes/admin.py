"""Endpoints del administrador (US-28). Todos responden 403 a una cuenta de jugador."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.api.dependencias import AdminActual, SessionDep
from app.models.partida import EstadoPartida
from app.realtime.gestor_motores import gestor_motores
from app.realtime.motor_partida import EN_CURSO
from app.realtime.reglas_victoria import POR_ADMINISTRADOR
from app.repositories import PartidaRepository, UsuarioRepository
from app.services.admin_service import (
    AdminService,
    BloqueoNoPermitidoError,
    UsuarioNoEncontradoError,
)
from app.services.partida_service import PartidaNoDisponibleError, PartidaNoEncontradaError

router = APIRouter(prefix="/admin", tags=["administración"])


class MejorPuntajeResponse(BaseModel):
    nombre: str
    puntaje: int
    partida_id: int


class EstadisticasResponse(BaseModel):
    usuarios_registrados: int
    usuarios_bloqueados: int
    partidas_jugadas: int
    partidas_activas: int
    mejores_puntajes: list[MejorPuntajeResponse]


class UsuarioAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_usuario: str
    correo: str
    rol: str
    bloqueado: bool
    fecha_registro: datetime | None


class PartidaActivaResponse(BaseModel):
    id: int
    estado: EstadoPartida
    escenario: str | None
    jugadores: int


def _servicio(db) -> AdminService:
    return AdminService(UsuarioRepository(db), PartidaRepository(db))


@router.get("/estadisticas", response_model=EstadisticasResponse)
def estadisticas(admin: AdminActual, db: SessionDep):
    return _servicio(db).estadisticas()


@router.get("/usuarios", response_model=list[UsuarioAdminResponse])
def listar_usuarios(admin: AdminActual, db: SessionDep):
    return UsuarioRepository(db).listar()


def _cambiar_bloqueo(admin, db, usuario_id: int, bloquear: bool):
    try:
        return _servicio(db).cambiar_bloqueo(admin, usuario_id, bloquear)
    except UsuarioNoEncontradoError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except BloqueoNoPermitidoError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error


@router.post("/usuarios/{usuario_id}/bloquear", response_model=UsuarioAdminResponse)
def bloquear(usuario_id: int, admin: AdminActual, db: SessionDep):
    return _cambiar_bloqueo(admin, db, usuario_id, bloquear=True)


@router.post("/usuarios/{usuario_id}/desbloquear", response_model=UsuarioAdminResponse)
def desbloquear(usuario_id: int, admin: AdminActual, db: SessionDep):
    return _cambiar_bloqueo(admin, db, usuario_id, bloquear=False)


@router.get("/partidas", response_model=list[PartidaActivaResponse])
def partidas_activas(admin: AdminActual, db: SessionDep):
    return [
        PartidaActivaResponse(
            id=partida.id, estado=partida.estado, escenario=partida.escenario, jugadores=total
        )
        for partida, total in PartidaRepository(db).listar_activas_con_jugadores()
    ]


@router.post("/partidas/{partida_id}/cerrar", status_code=status.HTTP_202_ACCEPTED)
async def cerrar_partida(partida_id: int, admin: AdminActual, db: SessionDep):
    """Cierra una partida colgada. Si está corriendo, el motor la termina y se guarda el
    resultado como en cualquier final; si no, solo se marca como finalizada en la base."""
    servicio = _servicio(db)
    try:
        partida = servicio.partida_activa(partida_id)
    except PartidaNoEncontradaError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except PartidaNoDisponibleError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    motor = gestor_motores.existente(partida_id)
    if motor is not None and motor.estado_partida == EN_CURSO:
        motor.terminar(POR_ADMINISTRADOR)
    else:
        servicio.cerrar_sin_motor(partida)
    return {"detail": f"La partida {partida_id} se cerró"}
