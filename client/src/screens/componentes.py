"""Componentes de interfaz reutilizables entre pantallas."""

import pygame

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
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.activo = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.activo:
            if event.key == pygame.K_BACKSPACE:
                self.texto = self.texto[:-1]
            elif event.unicode.isprintable() and len(self.texto) < self.largo_maximo:
                self.texto += event.unicode

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
    ) -> None:
        self.rect = rect
        self.texto = texto
        self.color = color
        self.color_hover = color_hover
        self.fuente = pygame.font.Font(None, 32)

    def fue_presionado(self, event: pygame.event.Event) -> bool:
        clic_izquierdo = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
        return clic_izquierdo and self.rect.collidepoint(event.pos)

    def draw(self, screen: pygame.Surface) -> None:
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        color = self.color_hover if hover else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        etiqueta = self.fuente.render(self.texto, True, (255, 255, 255))
        screen.blit(etiqueta, etiqueta.get_rect(center=self.rect.center))
