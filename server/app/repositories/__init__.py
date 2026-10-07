"""Acceso a datos con el patrón Repository. Rol B, US-21."""
from app.repositories.partida_repository import PartidaRepository
from app.repositories.usuario_repository import UsuarioRepository

__all__ = ["PartidaRepository", "UsuarioRepository"]