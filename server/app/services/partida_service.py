"""Servicio de partidas (US-07 y US-08)."""

from app.models.partida import EstadoPartida, Partida
from app.repositories import PartidaRepository
from app.services.partida_factory import MAX_JUGADORES, PartidaFactory


class JugadorYaEnPartidaError(Exception):
    """RN-04: un jugador no puede estar en más de una partida a la vez."""


class PartidaNoEncontradaError(Exception):
    """La partida pedida no existe."""


class PartidaNoDisponibleError(Exception):
    """La partida ya empezó o terminó y no acepta más jugadores."""


class PartidaLlenaError(Exception):
    """La partida ya alcanzó el máximo de jugadores."""


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

    def listar_disponibles(self) -> list[tuple[Partida, int]]:
        """Partidas esperando jugadores, junto con cuántos hay dentro."""
        return self.repo.listar_disponibles_con_jugadores()

    def unirse_a_partida(self, partida_id: int, jugador_id: int) -> tuple[Partida, int]:
        """Mete al jugador en una partida y devuelve cuántos hay ahora dentro."""
        partida = self.repo.obtener_por_id(partida_id)
        if partida is None:
            raise PartidaNoEncontradaError(f"La partida {partida_id} no existe")
        if partida.estado != EstadoPartida.esperando:
            raise PartidaNoDisponibleError(
                f"La partida {partida_id} ya no acepta jugadores"
            )
        if self.repo.jugador_en_partida_activa(jugador_id):
            raise JugadorYaEnPartidaError(
                f"El jugador {jugador_id} ya está en una partida activa"
            )
        if self.repo.contar_participantes(partida_id) >= MAX_JUGADORES:
            raise PartidaLlenaError(f"La partida {partida_id} está llena")
        self.repo.agregar_participante(partida_id, jugador_id)
        return partida, self.repo.contar_participantes(partida_id)
    def es_participante(self, partida_id: int, jugador_id: int) -> bool:
        return self.repo.es_participante(partida_id, jugador_id)