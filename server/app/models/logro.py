from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.db.session import Base


class LogroJugador(Base):
    """Un logro que un jugador ya desbloqueó (US-27). Cada logro se gana una sola vez."""

    __tablename__ = "logros_jugador"
    __table_args__ = (UniqueConstraint("jugador_id", "logro", name="uq_logro_por_jugador"),)

    id = Column(Integer, primary_key=True)
    jugador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    logro = Column(String(50), nullable=False)  # clave del catálogo (app/realtime/logros.py)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=True)
    obtenido_en = Column(DateTime, default=lambda: datetime.now(UTC))
