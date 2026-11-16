"""Estados del jugador en la arena (US-15, patrón State, ADR 0006).

El contexto es `JugadorEnArena`: guarda su estado actual y le pregunta qué puede hacer.
Cada estado decide a cuál pasa:

    Normal --golpe de guardián--> Aturdido --pasa el tiempo--> Escudado --pasa el tiempo--> Normal

Aturdido no se puede mover. Escudado se mueve, pero un guardián no lo penaliza (CU-11, E1);
sirve para que un guardián no lo golpee otra vez apenas se recupera.
"""

NORMAL = "normal"
ESCUDADO = "escudado"
ATURDIDO = "aturdido"

DURACION_ATURDIDO_S = 3.0
DURACION_ESCUDO_S = 2.0


class EstadoJugador:
    nombre: str = ""
    puede_moverse: bool = True
    vulnerable: bool = True  # si un guardián lo puede penalizar

    def actualizar(self, dt: float) -> "EstadoJugador":
        """Avanza el tiempo. Devuelve el estado en el que queda (puede ser el mismo)."""
        return self

    def golpeado(self) -> "EstadoJugador":
        """Estado en el que queda el jugador al ser alcanzado por un guardián."""
        return self


class Normal(EstadoJugador):
    nombre = NORMAL

    def golpeado(self) -> EstadoJugador:
        return Aturdido()


class Aturdido(EstadoJugador):
    nombre = ATURDIDO
    puede_moverse = False
    vulnerable = False  # ya está penalizado: no se le suma otro golpe

    def __init__(self, duracion_s: float = DURACION_ATURDIDO_S) -> None:
        self._restante = duracion_s

    def actualizar(self, dt: float) -> EstadoJugador:
        self._restante -= dt
        return Escudado() if self._restante <= 0 else self


class Escudado(EstadoJugador):
    nombre = ESCUDADO
    vulnerable = False

    def __init__(self, duracion_s: float = DURACION_ESCUDO_S) -> None:
        self._restante = duracion_s

    def actualizar(self, dt: float) -> EstadoJugador:
        self._restante -= dt
        return Normal() if self._restante <= 0 else self