from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.db.session import Base


class Evento(Base):
    __tablename__ = "eventos"

    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    tipo = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))