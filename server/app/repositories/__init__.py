"""Acceso a datos con el patrón Repository. Rol B, US-21."""
from app.repositories.evento_repository import EventoRepository
from app.repositories.logro_repository import LogroRepository
from app.repositories.partida_repository import PartidaRepository
from app.repositories.ranking_repository import RankingRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.usuario_repository import UsuarioRepository

__all__ = [
    "EventoRepository",
    "LogroRepository",
    "PartidaRepository",
    "RankingRepository",
    "TokenRepository",
    "UsuarioRepository",
]
