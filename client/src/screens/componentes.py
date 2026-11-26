"""Componentes de interfaz reutilizables entre pantallas."""

import pygame

from src import navegador

# Toques en el celular. Android manda el dedo (FINGERDOWN) y además un clic de mouse inventado a
# partir de él; el iPhone (Safari) solo manda el dedo. Por eso los botones y campos aceptan las dos
# cosas, y una vez que se vio un dedo se ignoran los clics de mouse para no presionar dos veces.
_dedos_vistos = False


def reiniciar_toques() -> None:
    """Olvida si ya se vieron dedos (lo usan las pruebas)."""
    global _dedos_vistos
    _dedos_vistos = False


def punto_presionado(event: pygame.event.Event) -> tuple[float, float] | None:
    """Dónde se presionó, en píxeles de la ventana, o None si el evento no es una presión."""
    global _dedos_vistos
    if event.type == pygame.FINGERDOWN:
        _dedos_vistos = True
        superficie = pygame.display.get_surface()
        ancho, alto = superficie.get_size() if superficie is not None else (1, 1)
        return event.x * ancho, event.y * alto  # los dedos vienen normalizados de 0 a 1
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not _dedos_vistos:
        return event.pos
    return None

COLOR_CAMPO = (24, 32, 56)
COLOR_BORDE = (60, 80, 120)
COLOR_BORDE_ACTIVO = (80, 200, 255)
COLOR_TEXTO = (230, 230, 240)
COLOR_ETIQUETA = (150, 160, 190)


class CampoTexto:
    def __init__(
        self,
        rect: pygame.Rect,
        etiqueta: str,
        oculto: bool = False,
        largo_maximo: int = 120,
    ) -> None:
        self.rect = rect
        self.etiqueta = etiqueta
        self.oculto = oculto
        self.largo_maximo = largo_maximo
        self.texto = ""
        self.activo = False
        self.fuente = pygame.font.Font(None, 30)
        self.fuente_etiqueta = pygame.font.Font(None, 24)

    def handle_event(self, event: pygame.event.Event) -> None:
        punto = punto_presionado(event)
        if punto is not None:
            self.activo = self.rect.collidepoint(punto)
            if self.activo:
                self._pedir_en_celular()
        elif event.type == pygame.KEYDOWN and self.activo:
            if event.key == pygame.K_BACKSPACE:
                self.texto = self.texto[:-1]
            elif event.unicode.isprintable() and len(self.texto) < self.largo_maximo:
                self.texto += event.unicode

    def _pedir_en_celular(self) -> None:
        """En el celular, tocar el campo abre el cuadro de texto del navegador con el teclado."""
        valor = navegador.pedir_texto(self.etiqueta, "" if self.oculto else self.texto)
        if valor is None:
            return
        limpio = "".join(c for c in valor if c.isprintable())
        self.texto = limpio[: self.largo_maximo]

    def draw(self, screen: pygame.Surface) -> None:
        etiqueta = self.fuente_etiqueta.render(self.etiqueta, True, COLOR_ETIQUETA)
        screen.blit(etiqueta, (self.rect.x, self.rect.y - 22))

        pygame.draw.rect(screen, COLOR_CAMPO, self.rect, border_radius=6)
        borde = COLOR_BORDE_ACTIVO if self.activo else COLOR_BORDE
        pygame.draw.rect(screen, borde, self.rect, width=2, border_radius=6)

        visible = "*" * len(self.texto) if self.oculto else self.texto
        texto = self.fuente.render(visible, True, COLOR_TEXTO)
        # si el texto es muy largo se ve solo el final
        ancho_util = self.rect.width - 20
        recorte = max(0, texto.get_width() - ancho_util)
        screen.blit(
            texto,
            (self.rect.x + 10, self.rect.centery - texto.get_height() // 2),
            area=pygame.Rect(recorte, 0, ancho_util, texto.get_height()),
        )


class Boton:
    def __init__(
        self,
        rect: pygame.Rect,
        texto: str,
        color: tuple[int, int, int] = (40, 120, 200),
        color_hover: tuple[int, int, int] = (70, 160, 240),
        color_texto: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        self.rect = rect
        self.texto = texto
        self.color = color
        self.color_hover = color_hover
        self.color_texto = color_texto
        self.fuente = pygame.font.Font(None, 32)

    def fue_presionado(self, event: pygame.event.Event) -> bool:
        punto = punto_presionado(event)
        return punto is not None and self.rect.collidepoint(punto)

    def draw(self, screen: pygame.Surface) -> None:
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        color = self.color_hover if hover else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        etiqueta = self.fuente.render(self.texto, True, self.color_texto)
        screen.blit(etiqueta, etiqueta.get_rect(center=self.rect.center))


def boton_secundario(rect: pygame.Rect, texto: str) -> Boton:
    return Boton(rect, texto, color=(40, 50, 80), color_hover=(60, 75, 115))
