"""Fuente de entrada del teclado (flechas o WASD y espacio), con el mapeo del contrato de hardware.

Solo avisa los cambios: si la tecla ya estaba presionada (por ejemplo con repetición de teclas
activada) no vuelve a enviar "presionado". Si la ventana pierde el foco, suelta todo, porque en
ese caso pygame no entrega los KEYUP y el jugador seguiría moviéndose.
"""

import pygame

from .base import FuenteEntrada

TECLAS = {
    pygame.K_UP: "arriba", pygame.K_w: "arriba",
    pygame.K_DOWN: "abajo", pygame.K_s: "abajo",
    pygame.K_LEFT: "izquierda", pygame.K_a: "izquierda",
    pygame.K_RIGHT: "derecha", pygame.K_d: "derecha",
    pygame.K_SPACE: "accion",
}  # fmt: skip


class Teclado(FuenteEntrada):
    origen = "teclado"

    def __init__(self) -> None:
        super().__init__()
        self._teclas_abajo: set[int] = set()
        self._presionados: set[str] = set()

    def procesar(self, evento) -> None:
        if evento.type == pygame.KEYDOWN and evento.key in TECLAS:
            self._teclas_abajo.add(evento.key)
        elif evento.type == pygame.KEYUP and evento.key in TECLAS:
            self._teclas_abajo.discard(evento.key)
        elif evento.type == pygame.WINDOWFOCUSLOST:
            self._teclas_abajo.clear()
        else:
            return
        self._actualizar()

    def _actualizar(self) -> None:
        # Un control sigue presionado mientras quede alguna de sus teclas abajo
        # (por ejemplo, flecha arriba y W a la vez).
        ahora = {TECLAS[tecla] for tecla in self._teclas_abajo}
        for control in sorted(ahora - self._presionados):
            self._pendientes.append((control, "presionado"))
        for control in sorted(self._presionados - ahora):
            self._pendientes.append((control, "liberado"))
        self._presionados = ahora
