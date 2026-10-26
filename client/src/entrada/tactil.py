"""Fuente de entrada táctil: cruceta y botón de acción dibujados en la pantalla (versión móvil).

Viene del prototipo móvil (ADR 0002), donde se probó en el celular:
- soporta varios dedos a la vez (moverse y presionar acción);
- si el dispositivo manda eventos de dedo, ignora los de mouse que el navegador genera con ellos;
- en cada cuadro revisa qué dedos siguen en la pantalla y suelta los botones que quedaron sin
  dedo, porque el navegador a veces cancela el toque y no llega el evento de soltar.
"""

import pygame

from .base import FuenteEntrada

TAMANO_BOTON = 74
MARGEN = 30


class Tactil(FuenteEntrada):
    origen = "tactil"

    def __init__(self, ancho: int, alto: int) -> None:
        super().__init__()
        self.ancho, self.alto = ancho, alto
        t = TAMANO_BOTON
        cx, cy = MARGEN + int(t * 1.5), alto - MARGEN - int(t * 1.5)
        lado_accion = int(t * 1.4)
        self.botones = {
            "arriba": pygame.Rect(cx - t // 2, cy - int(t * 1.5), t, t),
            "abajo": pygame.Rect(cx - t // 2, cy + t // 2, t, t),
            "izquierda": pygame.Rect(cx - int(t * 1.5), cy - t // 2, t, t),
            "derecha": pygame.Rect(cx + t // 2, cy - t // 2, t, t),
            "accion": pygame.Rect(
                ancho - MARGEN - lado_accion, alto - MARGEN - lado_accion, lado_accion, lado_accion
            ),
        }
        self._punteros: dict[str, str | None] = {}  # dedo o mouse -> control debajo
        self._presionados: set[str] = set()
        self._hay_dedos = False

    def control_en(self, x: float, y: float) -> str | None:
        for control, rect in self.botones.items():
            if rect.inflate(16, 16).collidepoint(x, y):
                return control
        return None

    def procesar(self, evento) -> None:
        tipo = evento.type
        if tipo in (pygame.FINGERDOWN, pygame.FINGERMOTION):
            self._hay_dedos = True
            x, y = evento.x * self.ancho, evento.y * self.alto  # vienen normalizados de 0 a 1
            self._punteros[f"dedo{evento.finger_id}"] = self.control_en(x, y)
        elif tipo == pygame.FINGERUP:
            self._punteros.pop(f"dedo{evento.finger_id}", None)
        elif self._hay_dedos:
            return  # eventos de mouse que el navegador generó a partir del toque
        elif tipo == pygame.MOUSEBUTTONDOWN or (
            tipo == pygame.MOUSEMOTION and "mouse" in self._punteros
        ):
            self._punteros["mouse"] = self.control_en(*evento.pos)
        elif tipo == pygame.MOUSEBUTTONUP:
            self._punteros.pop("mouse", None)
        elif tipo == pygame.WINDOWFOCUSLOST:
            self._punteros.clear()
        else:
            return
        self._actualizar()

    def revisar(self) -> None:
        cambio = False
        if "mouse" in self._punteros and not pygame.mouse.get_pressed()[0]:
            del self._punteros["mouse"]
            cambio = True
        activos = dedos_en_pantalla()
        if activos is not None:
            for clave in [k for k in self._punteros if k.startswith("dedo")]:
                if int(clave[4:]) not in activos:
                    del self._punteros[clave]
                    cambio = True
        if cambio:
            self._actualizar()

    def _actualizar(self) -> None:
        ahora = {c for c in self._punteros.values() if c is not None}
        for control in sorted(ahora - self._presionados):
            self._pendientes.append((control, "presionado"))
        for control in sorted(self._presionados - ahora):
            self._pendientes.append((control, "liberado"))
        self._presionados = ahora

    def dibujar(self, pantalla) -> None:
        capa = pygame.Surface((self.ancho, self.alto), pygame.SRCALPHA)
        for control, rect in self.botones.items():
            color = (120, 220, 255, 170) if control in self._presionados else (255, 255, 255, 60)
            if control == "accion":
                pygame.draw.ellipse(capa, color, rect)
            else:
                pygame.draw.rect(capa, color, rect, border_radius=14)
        pantalla.blit(capa, (0, 0))


def dedos_en_pantalla() -> set[int] | None:
    """Ids de los dedos que siguen tocando la pantalla, o None si no se puede saber."""
    try:
        from pygame._sdl2 import touch

        if touch.get_num_devices() == 0:
            return None  # sin pantalla táctil registrada: no hay con qué comparar
        ids = set()
        for i in range(touch.get_num_devices()):
            dispositivo = touch.get_device(i)
            for j in range(touch.get_num_fingers(dispositivo)):
                dedo = touch.get_finger(dispositivo, j)
                if dedo is not None:
                    ids.add(int(dedo["id"]))
        return ids
    except Exception:  # noqa: BLE001 - versión de pygame sin esta API
        return None
