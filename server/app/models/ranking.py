from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer

from app.db.session import Base


class RankingGlobal(Base):
    __tablename__ = "ranking_global"

    jugador_id = Column(Integer, ForeignKey("usuarios.id"), primary_key=True)
    puntos_totales = Column(Integer, default=0)
    victorias = Column(Integer, default=0)
    actualizado_en = Column(DateTime, default=lambda: datetime.now(UTC))