"""Aviso en la arena sobre el control físico (US-26).

`EntradaSerial` ya detecta cuándo el control se desconecta (3 s sin mensajes o el cable
desconectado) y cuándo vuelve. Esta clase decide qué ve el jugador:

- mientras el control no está conectado, un aviso fijo que le dice que puede seguir con el
  teclado (el control se reconecta solo);
- cuando el control se conecta, un aviso de confirmación durante unos segundos.

Sin control físico configurado no se muestra nada. La lógica no depende de pygame, así se
prueba sin ventana; solo `dibujar` usa pygame.
"""

import time
from collections.abc import Callable
from typing import Any

DURACION_CONECTADO_S = 3.0  # cuánto se ve el aviso de "control conectado"

ESPERANDO = "Esperando el control físico... Podés jugar con el teclado."
DESCONECTADO = "Control desconectado. Seguí con el teclado; se reconecta solo."
CONECTADO = "Control conectado."

COLOR_ALERTA = (200, 120, 0)
COLOR_OK = (30, 150, 70)
COLOR_TEXTO = (255, 255, 255)


class AvisoControl:
    def __init__(self, reloj: Callable[[], float] = time.monotonic) -> None:
        self._reloj = reloj
        self._estuvo_conectado = False
        self._estado_anterior: str | None = None
        self._conectado_desde: float | None = None
        self._fuente: Any = None

    def observar(self, estado_control: str | None) -> None:
        """Se llama una vez por cuadro con el estado del control físico (None si no hay)."""
        if estado_control == "conectado" and self._estado_anterior != "conectado":
            self._conectado_desde = self._reloj()
        if estado_control == "conectado":
            self._estuvo_conectado = True
        else:
            self._conectado_desde = None
        self._estado_anterior = estado_control

    def mensaje(self) -> tuple[str, str] | None:
        """El aviso que se ve ahora: (texto, tipo), con tipo "alerta" u "ok"; o None."""
        estado = self._estado_anterior
        if estado is None:
            return None  # no hay control físico configurado
        if estado != "conectado":
            return (DESCONECTADO if self._estuvo_conectado else ESPERANDO, "alerta")
        if self._conectado_desde is not None:
            if self._reloj() - self._conectado_desde < DURACION_CONECTADO_S:
                return (CONECTADO, "ok")
        return None

    def dibujar(self, pantalla: Any) -> None:
        aviso = self.mensaje()
        if aviso is None:
            return
        import pygame

        texto, tipo = aviso
        if self._fuente is None:
            self._fuente = pygame.font.Font(None, 28)
        superficie = self._fuente.render(texto, True, COLOR_TEXTO)
        caja = superficie.get_rect(midtop=(pantalla.get_width() // 2, 12)).inflate(24, 12)
        color = COLOR_ALERTA if tipo == "alerta" else COLOR_OK
        pygame.draw.rect(pantalla, color, caja, border_radius=8)
        pantalla.blit(superficie, superficie.get_rect(center=caja.center))
