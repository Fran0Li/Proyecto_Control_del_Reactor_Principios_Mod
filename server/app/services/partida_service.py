"""Servicio de creación de partidas (US-07)."""

from app.models.partida import Partida
from app.repositories import PartidaRepository
from app.services.partida_factory import PartidaFactory


class JugadorYaEnPartidaError(Exception):
    """RN-04: un jugador no puede estar en más de una partida a la vez."""


class PartidaService:
    def __init__(
        self,
        repo: PartidaRepository,
        factory: PartidaFactory | None = None,
    ) -> None:
        self.repo = repo
        self.factory = factory or PartidaFactory()

    def crear_partida(
        self,
        creador_id: int,
        escenario: str | None = None,
    ) -> Partida:
        if self.repo.jugador_en_partida_activa(creador_id):
            raise JugadorYaEnPartidaError(
                f"El jugador {creador_id} ya está en una partida activa"
            )
        partida = self.repo.crear(self.factory.crear(escenario))
        self.repo.agregar_participante(partida.id, creador_id)
        return partida