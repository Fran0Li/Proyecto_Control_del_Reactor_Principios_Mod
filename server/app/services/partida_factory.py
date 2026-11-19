"""Fábrica de partidas (patrón Factory)."""

import random

from app.core.config import settings
from app.models.partida import EstadoPartida, Partida

ESCENARIOS = (
    "laboratorio",
    "estacion_espacial",
    "planta_industrial",
    "centro_investigacion",
    "complejo_militar",
)
TIEMPO_LIMITE_SEGUNDOS = settings.partida_tiempo_limite_s  # 300 si no se cambia en el .env
PUNTUACION_OBJETIVO = settings.partida_puntaje_objetivo  # 500 si no se cambia en el .env
MAX_JUGADORES = 4

    
class PartidaFactory:
    def crear(self, escenario: str | None = None) -> Partida:
        if escenario is not None and escenario not in ESCENARIOS:
            raise ValueError(f"Escenario no válido: {escenario}")
        return Partida(
            estado=EstadoPartida.esperando,
            escenario=escenario or random.choice(ESCENARIOS),
            tiempo_limite_segundos=TIEMPO_LIMITE_SEGUNDOS,
            puntuacion_objetivo=PUNTUACION_OBJETIVO,
        )