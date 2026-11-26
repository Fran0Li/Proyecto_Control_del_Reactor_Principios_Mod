from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.evento import Evento


class EventoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def agregar(
        self, partida_id: int, tipo: str, jugador_id: int | None = None, datos: dict | None = None
    ) -> Evento:
        evento = Evento(partida_id=partida_id, tipo=tipo, jugador_id=jugador_id, datos=datos)
        self.db.add(evento)
        self.db.commit()
        return evento

    def contar_por_jugador(self, partida_id: int, tipo: str) -> dict[int, int]:
        """Cuántos eventos de un tipo tuvo cada jugador en la partida."""
        consulta = (
            select(Evento.jugador_id, func.count())
            .where(Evento.partida_id == partida_id, Evento.tipo == tipo)
            .where(Evento.jugador_id.is_not(None))
            .group_by(Evento.jugador_id)
        )
        return {jugador_id: total for jugador_id, total in self.db.execute(consulta).all()}

    def ultimo(self, partida_id: int, tipo: str) -> Evento | None:
        consulta = (
            select(Evento)
            .where(Evento.partida_id == partida_id, Evento.tipo == tipo)
            .order_by(Evento.id.desc())
        )
        return self.db.scalars(consulta).first()
