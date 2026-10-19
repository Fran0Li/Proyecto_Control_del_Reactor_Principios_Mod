import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

CONTROLES = {"arriba", "abajo", "izquierda", "derecha", "accion"}
ESTADOS = {"presionado", "liberado"}
MAX_ENTRADAS_POR_SEGUNDO = 30


class EntradaInvalida(ValueError):
    """El mensaje de entrada no cumple el contrato."""


@dataclass(frozen=True)
class Entrada:
    control: str
    estado: str
    seq: int | None


def interpretar_entrada(mensaje: dict) -> Entrada:
    control = mensaje.get("control")
    if control not in CONTROLES:
        raise EntradaInvalida(f"control desconocido: {control}")
    estado = mensaje.get("estado")
    if estado not in ESTADOS:
        raise EntradaInvalida(f"estado desconocido: {estado}")
    seq = mensaje.get("seq")
    if seq is not None and (not isinstance(seq, int) or isinstance(seq, bool)):
        raise EntradaInvalida("seq debe ser un entero")
    return Entrada(control, estado, seq)


class FiltroEntradas:
    """Uno por conexión: descarta lo repetido o atrasado (seq) y lo que pase de 30 por segundo."""

    def __init__(self, reloj: Callable[[], float] = time.monotonic) -> None:
        self._reloj = reloj
        self._marcas: deque[float] = deque()
        self._ultima_seq: int | None = None

    def admite(self, entrada: Entrada) -> bool:
        ahora = self._reloj()
        while self._marcas and ahora - self._marcas[0] >= 1.0:
            self._marcas.popleft()
        if len(self._marcas) >= MAX_ENTRADAS_POR_SEGUNDO:
            return False
        if entrada.seq is not None:
            if self._ultima_seq is not None and entrada.seq <= self._ultima_seq:
                return False
            self._ultima_seq = entrada.seq
        self._marcas.append(ahora)
        return True