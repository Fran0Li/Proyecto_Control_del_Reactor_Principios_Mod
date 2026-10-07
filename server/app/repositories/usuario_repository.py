from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario import Usuario


class UsuarioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def crear(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def obtener_por_id(self, usuario_id: int) -> Usuario | None:
        return self.db.get(Usuario, usuario_id)

    def obtener_por_correo(self, correo: str) -> Usuario | None:
        consulta = select(Usuario).where(Usuario.correo == correo)
        return self.db.scalars(consulta).first()

    def obtener_por_nombre_usuario(self, nombre_usuario: str) -> Usuario | None:
        consulta = select(Usuario).where(Usuario.nombre_usuario == nombre_usuario)
        return self.db.scalars(consulta).first()

    def existe_correo(self, correo: str) -> bool:
        return self.obtener_por_correo(correo) is not None

    def existe_nombre_usuario(self, nombre_usuario: str) -> bool:
        return self.obtener_por_nombre_usuario(nombre_usuario) is not None