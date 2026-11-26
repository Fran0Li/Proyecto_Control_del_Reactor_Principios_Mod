from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.logro import LogroJugador


class LogroRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def claves_obtenidas(self, jugador_id: int) -> set[str]:
        consulta = select(LogroJugador.logro).where(LogroJugador.jugador_id == jugador_id)
        return set(self.db.scalars(consulta))

    def de_jugador(self, jugador_id: int) -> list[LogroJugador]:
        consulta = (
            select(LogroJugador)
            .where(LogroJugador.jugador_id == jugador_id)
            .order_by(LogroJugador.obtenido_en, LogroJugador.id)
        )
        return list(self.db.scalars(consulta))

    def de_partida(self, partida_id: int) -> list[LogroJugador]:
        """Los logros que se desbloquearon en una partida (para la ceremonia, US-18)."""
        consulta = (
            select(LogroJugador)
            .where(LogroJugador.partida_id == partida_id)
            .order_by(LogroJugador.id)
        )
        return list(self.db.scalars(consulta))

    def agregar(self, jugador_id: int, claves: Iterable[str], partida_id: int | None) -> None:
        """Guarda logros nuevos. Quien llama ya descartó los que el jugador tenía; la restricción
        única de la tabla evita duplicados aunque dos evaluaciones coincidan."""
        for clave in claves:
            self.db.add(LogroJugador(jugador_id=jugador_id, logro=clave, partida_id=partida_id))
        self.db.commit()
