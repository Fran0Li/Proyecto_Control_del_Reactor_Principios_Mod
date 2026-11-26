from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.ranking import RankingGlobal
from app.models.usuario import Usuario

# más puntos primero; si empatan, más victorias
ORDEN = (RankingGlobal.puntos_totales.desc(), RankingGlobal.victorias.desc())


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

    def top(self, limite: int) -> list[tuple[RankingGlobal, str]]:
        """Los mejores jugadores con su nombre de usuario."""
        consulta = (
            select(RankingGlobal, Usuario.nombre_usuario)
            .join(Usuario, Usuario.id == RankingGlobal.jugador_id)
            .order_by(*ORDEN, RankingGlobal.jugador_id)
            .limit(limite)
        )
        return [(fila, nombre) for fila, nombre in self.db.execute(consulta).all()]

    def de_jugador(self, jugador_id: int) -> RankingGlobal | None:
        return self.db.get(RankingGlobal, jugador_id)

    def posicion(self, fila: RankingGlobal) -> int:
        """Puesto del jugador: 1 + cuántos tienen más puntos (o iguales puntos y más victorias)."""
        mejores = select(func.count()).where(
            or_(
                RankingGlobal.puntos_totales > fila.puntos_totales,
                (RankingGlobal.puntos_totales == fila.puntos_totales)
                & (RankingGlobal.victorias > fila.victorias),
            )
        )
        return (self.db.scalar(mejores) or 0) + 1
