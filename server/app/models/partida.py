from sqlalchemy import Column, Integer, String, DateTime, Enum
from datetime import datetime
import enum

from app.db.session import Base


class EstadoPartida(enum.Enum):
    esperando = "esperando"
    en_curso = "en_curso"
    finalizada = "finalizada"


class Partida(Base):
    __tablename__ = "partidas"

    id = Column(Integer, primary_key=True)
    estado = Column(Enum(EstadoPartida), default=EstadoPartida.esperando)
    escenario = Column(String(50))
    tiempo_limite_segundos = Column(Integer)
    puntuacion_objetivo = Column(Integer)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)