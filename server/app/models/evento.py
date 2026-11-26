from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String

from app.db.session import Base


class Evento(Base):
    __tablename__ = "eventos"

    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    tipo = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    # quién lo provocó (vacío en los de toda la partida) y el detalle del evento (US-17)
    jugador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    datos = Column(JSON, nullable=True)
