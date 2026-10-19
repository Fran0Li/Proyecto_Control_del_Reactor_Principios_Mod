"""Resultados del login con Google mientras el juego los espera (US-04).

El juego abre el navegador con un id de sesión al azar y pregunta cada segundo si ese login ya
terminó. Los resultados se guardan en memoria unos minutos y se entregan una sola vez.
"""

import time
from threading import Lock

SEGUNDOS_VALIDEZ = 300


class SesionesGoogle:
    def __init__(self) -> None:
        self._resultados: dict[str, tuple[float, dict]] = {}
        self._lock = Lock()

    def guardar(self, sesion_id: str, resultado: dict) -> None:
        with self._lock:
            self._limpiar()
            self._resultados[sesion_id] = (time.monotonic(), resultado)

    def tomar(self, sesion_id: str) -> dict | None:
        with self._lock:
            self._limpiar()
            guardado = self._resultados.pop(sesion_id, None)
        return guardado[1] if guardado else None

    def _limpiar(self) -> None:
        limite = time.monotonic() - SEGUNDOS_VALIDEZ
        for clave in [c for c, (creado, _) in self._resultados.items() if creado < limite]:
            del self._resultados[clave]


sesiones_google = SesionesGoogle()
