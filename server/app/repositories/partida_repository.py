from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.participacion import Participacion
from app.models.partida import EstadoPartida, Partida

ESTADOS_ACTIVOS = (EstadoPartida.esperando, EstadoPartida.en_curso)


class PartidaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def crear(self, partida: Partida) -> Partida:
        self.db.add(partida)
        self.db.commit()
        self.db.refresh(partida)
        return partida

    def obtener_por_id(self, partida_id: int) -> Partida | None:
        return self.db.get(Partida, partida_id)

    def listar_disponibles(self) -> list[Partida]:
        consulta = select(Partida).where(Partida.estado == EstadoPartida.esperando)
        return list(self.db.scalars(consulta).all())

    def cambiar_estado(self, partida: Partida, estado: EstadoPartida) -> Partida:
        partida.estado = estado
        if estado == EstadoPartida.en_curso:
            partida.fecha_inicio = datetime.now(UTC)
        elif estado == EstadoPartida.finalizada:
            partida.fecha_fin = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(partida)
        return partida

    def agregar_participante(self, partida_id: int, jugador_id: int) -> Participacion:
        participacion = Participacion(partida_id=partida_id, jugador_id=jugador_id)
        self.db.add(participacion)
        self.db.commit()
        self.db.refresh(participacion)
        return participacion

    def listar_participaciones(self, partida_id: int) -> list[Participacion]:
        consulta = select(Participacion).where(Participacion.partida_id == partida_id)
        return list(self.db.scalars(consulta).all())

    def contar_participantes(self, partida_id: int) -> int:
        consulta = (
            select(func.count())
            .select_from(Participacion)
            .where(Participacion.partida_id == partida_id)
        )
        return self.db.scalar(consulta) or 0

    def jugador_en_partida_activa(self, jugador_id: int) -> bool:
        """Sirve para validar RN-04: un jugador no puede estar en dos partidas a la vez."""
        consulta = (
            select(Participacion.id)
            .join(Partida, Partida.id == Participacion.partida_id)
            .where(Participacion.jugador_id == jugador_id)
            .where(Partida.estado.in_(ESTADOS_ACTIVOS))
        )
        return self.db.scalars(consulta).first() is not None