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
