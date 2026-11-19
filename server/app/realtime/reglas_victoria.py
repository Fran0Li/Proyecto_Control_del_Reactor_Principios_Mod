"""Cuándo termina una partida y en qué orden quedan los jugadores (US-17 y US-22).

La partida termina por lo que pase primero: se acaba el tiempo (300 s) o alguien llega a la
puntuación objetivo (500). Al terminar se ordena a los jugadores por puntaje; quienes empatan
comparten el puesto (1, 1, 3...). Si hay empate en el primer lugar no hay ganador único.
"""

from dataclasses import dataclass

POR_TIEMPO = "tiempo"
POR_PUNTAJE = "puntaje"
POR_ADMINISTRADOR = "administrador"  # un admin cerró la partida (US-28)


@dataclass(frozen=True)
class Posicion:
    jugador_id: int
    nombre: str
    puntaje: int
    posicion: int  # 1 = primer lugar

    def a_dict(self) -> dict:
        return {
            "jugador_id": self.jugador_id,
            "nombre": self.nombre,
            "puntaje": self.puntaje,
            "posicion": self.posicion,
        }


class ReglasVictoria:
    def __init__(self, tiempo_limite_s: float, puntaje_objetivo: int) -> None:
        self.tiempo_limite_s = tiempo_limite_s
        self.puntaje_objetivo = puntaje_objetivo

    def tiempo_restante(self, transcurrido: float) -> float:
        return max(0.0, self.tiempo_limite_s - transcurrido)

    def motivo_de_fin(self, transcurrido: float, puntajes: list[int]) -> str | None:
        """Por qué termina la partida ahora, o None si sigue."""
        if any(puntaje >= self.puntaje_objetivo for puntaje in puntajes):
            return POR_PUNTAJE
        if self.tiempo_restante(transcurrido) <= 0:
            return POR_TIEMPO
        return None


def ordenar(jugadores: list[tuple[int, str, int]]) -> list[Posicion]:
    """`jugadores` = (jugador_id, nombre, puntaje). Devuelve las posiciones de mayor a menor."""
    ordenados = sorted(jugadores, key=lambda j: (-j[2], j[0]))
    posiciones: list[Posicion] = []
    for indice, (jugador_id, nombre, puntaje) in enumerate(ordenados):
        if posiciones and posiciones[-1].puntaje == puntaje:
            puesto = posiciones[-1].posicion  # empate: mismo puesto que el anterior
        else:
            puesto = indice + 1
        posiciones.append(Posicion(jugador_id, nombre, puntaje, puesto))
    return posiciones


def ganador(posiciones: list[Posicion]) -> int | None:
    """El id del primer lugar, o None si no hay jugadores o hay empate arriba."""
    primeros = [p for p in posiciones if p.posicion == 1]
    return primeros[0].jugador_id if len(primeros) == 1 else None
