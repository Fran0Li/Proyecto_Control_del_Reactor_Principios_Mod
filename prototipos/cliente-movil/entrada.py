"""Fuentes de entrada del prototipo: teclado y botones táctiles en pantalla.

Todas cumplen la misma interfaz (patrón Adapter, como dice el contrato de hardware):
reciben eventos de pygame y entregan pares (control, estado) con los valores del contrato.
El control Arduino (Serial) se agregará después con esta misma interfaz.
"""

import pygame

CONTROLES = ("arriba", "abajo", "izquierda", "derecha", "accion")


class FuenteEntrada:
    origen = "?"

    def __init__(self) -> None:
        self._pendientes: list[tuple[str, str]] = []

    def procesar(self, evento: pygame.event.Event) -> None:
        raise NotImplementedError

    def obtener(self) -> list[tuple[str, str]]:
        pendientes, self._pendientes = self._pendientes, []
        return pendientes

    def revisar(self) -> None:
        """Opcional: se llama una vez por frame para corregir estados perdidos."""

    def dibujar(self, pantalla: pygame.Surface) -> None:
        """Opcional: las fuentes con interfaz visual (táctil) se dibujan aquí."""


class Teclado(FuenteEntrada):
    origen = "teclado"
    TECLAS = {
        pygame.K_UP: "arriba", pygame.K_w: "arriba",
        pygame.K_DOWN: "abajo", pygame.K_s: "abajo",
        pygame.K_LEFT: "izquierda", pygame.K_a: "izquierda",
        pygame.K_RIGHT: "derecha", pygame.K_d: "derecha",
        pygame.K_SPACE: "accion",
    }  # fmt: skip

    def procesar(self, evento: pygame.event.Event) -> None:
        if evento.type in (pygame.KEYDOWN, pygame.KEYUP) and evento.key in self.TECLAS:
            estado = "presionado" if evento.type == pygame.KEYDOWN else "liberado"
            self._pendientes.append((self.TECLAS[evento.key], estado))


class Tactil(FuenteEntrada):
    """Cruceta y botón de acción dibujados en pantalla.

    Soporta varios dedos a la vez (moverse y presionar acción). Si el dispositivo manda eventos
    de dedo, se ignoran los eventos de mouse que el navegador genera a partir de ellos.
    """

    origen = "tactil"

    def __init__(self, ancho: int, alto: int) -> None:
        super().__init__()
        self.ancho, self.alto = ancho, alto
        t = 74  # tamaño de cada botón
        cx, cy = 30 + int(t * 1.5), alto - 30 - int(t * 1.5)
        self.botones = {
            "arriba": pygame.Rect(cx - t // 2, cy - int(t * 1.5), t, t),
            "abajo": pygame.Rect(cx - t // 2, cy + t // 2, t, t),
            "izquierda": pygame.Rect(cx - int(t * 1.5), cy - t // 2, t, t),
            "derecha": pygame.Rect(cx + t // 2, cy - t // 2, t, t),
            "accion": pygame.Rect(ancho - 30 - int(t * 1.4), alto - 30 - int(t * 1.4),
                                  int(t * 1.4), int(t * 1.4)),
        }  # fmt: skip
        self._punteros: dict[str, str | None] = {}  # id de dedo o mouse -> control bajo él
        self._presionados: set[str] = set()
        self._hay_dedos = False
        self.registro: list[str] = []  # últimos eventos recibidos, para diagnosticar en el celular

    def _control_en(self, x: float, y: float) -> str | None:
        for control, rect in self.botones.items():
            if rect.inflate(16, 16).collidepoint(x, y):
                return control
        return None

    def _anotar(self, evento: pygame.event.Event) -> None:
        nombres = {
            pygame.FINGERDOWN: "dedo+", pygame.FINGERUP: "dedo-",
            pygame.MOUSEBUTTONDOWN: "mouse+", pygame.MOUSEBUTTONUP: "mouse-",
        }  # fmt: skip
        if evento.type in nombres:
            extra = f"{evento.finger_id}" if hasattr(evento, "finger_id") else ""
            self.registro = (self.registro + [nombres[evento.type] + extra])[-8:]

    def procesar(self, evento: pygame.event.Event) -> None:
        self._anotar(evento)
        tipo = evento.type
        if tipo in (pygame.FINGERDOWN, pygame.FINGERMOTION):
            self._hay_dedos = True
            x, y = evento.x * self.ancho, evento.y * self.alto  # vienen normalizados 0..1
            self._punteros[f"dedo{evento.finger_id}"] = self._control_en(x, y)
        elif tipo == pygame.FINGERUP:
            self._punteros.pop(f"dedo{evento.finger_id}", None)
        elif self._hay_dedos:
            return  # eventos de mouse sintéticos generados por el toque
        elif tipo == pygame.MOUSEBUTTONDOWN or (
            tipo == pygame.MOUSEMOTION and "mouse" in self._punteros
        ):
            self._punteros["mouse"] = self._control_en(*evento.pos)
        elif tipo == pygame.MOUSEBUTTONUP:
            self._punteros.pop("mouse", None)
        elif tipo == pygame.WINDOWFOCUSLOST:
            self._punteros.clear()
        else:
            return
        self._actualizar()

    def revisar(self) -> None:
        """Red de seguridad: suelta botones cuyo dedo o clic ya no existe.

        En el celular a veces se pierde el evento de "soltar" (el navegador cancela el toque),
        y el botón quedaba presionado. Aquí se compara con los dedos que siguen en pantalla.
        """
        cambio = False
        if "mouse" in self._punteros and not pygame.mouse.get_pressed()[0]:
            del self._punteros["mouse"]
            cambio = True
        activos = _dedos_en_pantalla()
        if activos is not None:
            for clave in [k for k in self._punteros if k.startswith("dedo")]:
                if int(clave[4:]) not in activos:
                    del self._punteros[clave]
                    cambio = True
        if cambio:
            self._actualizar()

    def _actualizar(self) -> None:
        ahora = {c for c in self._punteros.values() if c is not None}
        for control in ahora - self._presionados:
            self._pendientes.append((control, "presionado"))
        for control in self._presionados - ahora:
            self._pendientes.append((control, "liberado"))
        self._presionados = ahora

    def dibujar(self, pantalla: pygame.Surface) -> None:
        capa = pygame.Surface((self.ancho, self.alto), pygame.SRCALPHA)
        for control, rect in self.botones.items():
            activo = control in self._presionados
            color = (120, 220, 255, 170) if activo else (255, 255, 255, 60)
            if control == "accion":
                pygame.draw.ellipse(capa, color, rect)
            else:
                pygame.draw.rect(capa, color, rect, border_radius=14)
        pantalla.blit(capa, (0, 0))


def _dedos_en_pantalla() -> set[int] | None:
    """Ids de los dedos que siguen tocando la pantalla, o None si no se puede saber."""
    try:
        from pygame._sdl2 import touch

        if touch.get_num_devices() == 0:
            return None  # sin pantalla táctil registrada: no se puede comparar
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
