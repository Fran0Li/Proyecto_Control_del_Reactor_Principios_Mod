from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.db.session import Base


class TokenUsuario(Base):
    """Código de un solo uso que se manda por correo (verificar la cuenta o recuperar la clave).

    Solo se guarda el hash: si alguien lee la base de datos no puede usar los códigos.
    """

    __tablename__ = "tokens_usuario"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo = Column(String(20), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False)
    expira_en = Column(DateTime, nullable=False)
    usado_en = Column(DateTime, nullable=True)
