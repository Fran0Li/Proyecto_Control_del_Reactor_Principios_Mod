from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime, timezone

from app.db.session import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    nombre_usuario = Column(String(50), unique=True, nullable=False)
    correo = Column(String(120), unique=True, nullable=False)
    correo_verificado = Column(Boolean, default=False)
    contrasena_hash = Column(String(255), nullable=False)
    fecha_registro = Column(DateTime, default=datetime.now(timezone.utc))