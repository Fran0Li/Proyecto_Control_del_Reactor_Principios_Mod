from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy import false as sa_false

from app.db.session import Base

ROL_JUGADOR = "jugador"
ROL_ADMIN = "administrador"  # US-28: se crea con el script app/scripts/crear_admin.py


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    nombre_usuario = Column(String(50), unique=True, nullable=False)
    correo = Column(String(120), unique=True, nullable=False)
    correo_verificado = Column(Boolean, default=False)
    contrasena_hash = Column(String(255), nullable=True)  # vacío en cuentas solo de Google
    fecha_registro = Column(DateTime, default=lambda: datetime.now(UTC))
    intentos_fallidos = Column(Integer, nullable=False, default=0, server_default="0")
    bloqueado_hasta = Column(DateTime, nullable=True)
    version_sesion = Column(Integer, nullable=False, default=0, server_default="0")
    google_id = Column(String(64), unique=True, nullable=True)
    # perfil (US-06)
    descripcion = Column(String(200), nullable=False, default="", server_default="")
    avatar = Column(String(20), nullable=False, default="azul", server_default="azul")
    # administración (US-28)
    rol = Column(String(20), nullable=False, default=ROL_JUGADOR, server_default=ROL_JUGADOR)
    bloqueado = Column(Boolean, nullable=False, default=False, server_default=sa_false())
