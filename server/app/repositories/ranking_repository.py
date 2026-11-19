from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.ranking import RankingGlobal


class RankingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def sumar_partida(self, jugador_id: int, puntos: int, gano: bool) -> RankingGlobal:
        """Suma el resultado de una partida al acumulado del jugador (lo crea si no tenía)."""
        fila = self.db.get(RankingGlobal, jugador_id)
        if fila is None:
            fila = RankingGlobal(jugador_id=jugador_id, puntos_totales=0, victorias=0)
            self.db.add(fila)
        fila.puntos_totales = (fila.puntos_totales or 0) + puntos
        fila.victorias = (fila.victorias or 0) + (1 if gano else 0)
        fila.actualizado_en = datetime.now(UTC)
        self.db.commit()
        return fila
