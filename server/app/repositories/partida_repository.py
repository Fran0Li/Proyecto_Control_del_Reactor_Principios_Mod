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

    def cerrar_si_sigue_esperando(self, partida_id: int) -> bool:
        """Cierra una partida que nunca se inició (todos se fueron del lobby). True si la cerró."""
        partida = self.obtener_por_id(partida_id)
        if partida is None or partida.estado != EstadoPartida.esperando:
            return False
        self.cambiar_estado(partida, EstadoPartida.finalizada)
        return True

    def cerrar_activas(self) -> int:
        """Cierra todas las partidas en espera o en curso. Los motores viven en memoria: al
        arrancar el servidor ninguna puede seguir, y si quedaran activas, sus jugadores no
        podrían crear ni unirse a otra (RN-04). Devuelve cuántas cerró."""
        activas = self.db.scalars(select(Partida).where(Partida.estado.in_(ESTADOS_ACTIVOS)))
        cerradas = 0
        for partida in list(activas):
            partida.estado = EstadoPartida.finalizada
            partida.fecha_fin = datetime.now(UTC)
            cerradas += 1
        self.db.commit()
        return cerradas

    def guardar_resultado(self, partida: Partida, posiciones: dict[int, tuple[int, int]]) -> None:
        """Cierra la partida. `posiciones`: jugador_id -> (puntaje final, posición final)."""
        for participacion in self.listar_participaciones(partida.id):
            if participacion.jugador_id in posiciones:
                puntaje, posicion = posiciones[participacion.jugador_id]
                participacion.puntaje_final = puntaje
                participacion.posicion_final = posicion
        self.cambiar_estado(partida, EstadoPartida.finalizada)

    def agregar_participante(self, partida_id: int, jugador_id: int) -> Participacion:
        participacion = Participacion(partida_id=partida_id, jugador_id=jugador_id)
        self.db.add(participacion)
        self.db.commit()
        self.db.refresh(participacion)
        return participacion

    def listar_participaciones(self, partida_id: int) -> list[Participacion]:
        consulta = select(Participacion).where(Participacion.partida_id == partida_id)
        return list(self.db.scalars(consulta).all())

    def creador(self, partida_id: int) -> int | None:
        """El primero que entró a la partida es quien la creó (US-07)."""
        consulta = (
            select(Participacion.jugador_id)
            .where(Participacion.partida_id == partida_id)
            .order_by(Participacion.id)
        )
        return self.db.scalars(consulta).first()

    def contar_participantes(self, partida_id: int) -> int:
        consulta = (
            select(func.count())
            .select_from(Participacion)
            .where(Participacion.partida_id == partida_id) 
        )
        return self.db.scalar(consulta) or 0
    def listar_disponibles_con_jugadores(self) -> list[tuple[Partida, int]]:
        consulta = (
            select(Partida, func.count(Participacion.id))
            .outerjoin(Participacion, Participacion.partida_id == Partida.id)
            .where(Partida.estado == EstadoPartida.esperando)
            .group_by(Partida.id)
            .order_by(Partida.id)
        )
        return [(partida, total) for partida, total in self.db.execute(consulta).all()]
    def mejor_puntaje_antes(self, jugador_id: int, partida_id: int) -> int | None:
        """El mejor puntaje del jugador en las partidas que terminó antes de esta."""
        consulta = (
            select(func.max(Participacion.puntaje_final))
            .join(Partida, Partida.id == Participacion.partida_id)
            .where(Participacion.jugador_id == jugador_id)
            .where(Partida.estado == EstadoPartida.finalizada)
            .where(Partida.id < partida_id)
        )
        return self.db.scalar(consulta)

    def es_participante(self, partida_id: int, jugador_id: int) -> bool:
        consulta = (
            select(Participacion.id)
            .where(Participacion.partida_id == partida_id)
            .where(Participacion.jugador_id == jugador_id)
        )
        return self.db.scalars(consulta).first() is not None
    
    def jugador_en_partida_activa(self, jugador_id: int) -> bool:
        """Sirve para validar RN-04: un jugador no puede estar en dos partidas a la vez."""
        consulta = (
            select(Participacion.id)
            .join(Partida, Partida.id == Participacion.partida_id)
            .where(Participacion.jugador_id == jugador_id)
            .where(Partida.estado.in_(ESTADOS_ACTIVOS))
        )
        return self.db.scalars(consulta).first() is not None