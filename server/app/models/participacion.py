from sqlalchemy import Column, Integer, ForeignKey

from app.db.session import Base


class Participacion(Base):
    __tablename__ = "participaciones"

    id = Column(Integer, primary_key=True)
    jugador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    puntaje_final = Column(Integer, default=0)
    posicion_final = Column(Integer, nullable=True)