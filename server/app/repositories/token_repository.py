from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.token_usuario import TokenUsuario


class TokenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def crear(self, token: TokenUsuario) -> TokenUsuario:
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def buscar(self, token_hash: str, tipo: str) -> TokenUsuario | None:
        consulta = select(TokenUsuario).where(
            TokenUsuario.token_hash == token_hash, TokenUsuario.tipo == tipo
        )
        return self.db.scalars(consulta).first()

    def invalidar_pendientes(self, usuario_id: int, tipo: str, ahora: datetime) -> None:
        """Marca como usados los tokens que el usuario todavía no había usado."""
        self.db.execute(
            update(TokenUsuario)
            .where(
                TokenUsuario.usuario_id == usuario_id,
                TokenUsuario.tipo == tipo,
                TokenUsuario.usado_en.is_(None),
            )
            .values(usado_en=ahora)
        )
        self.db.commit()
