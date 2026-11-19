"""HUD de la partida: reloj y tabla de posiciones encima de la arena (US-24 y US-22).

Todo sale del estado que manda el servidor en cada cambio: el reloj usa
`estado["partida"]["tiempo_restante"]` y la tabla los puntajes de `estado["jugadores"]`.
Así todos los jugadores ven lo mismo.
"""

import pygame

POCO_TIEMPO_S = 30  # desde aquí el reloj se pone en rojo

COLOR_FONDO = (10, 14, 28, 190)
COLOR_TEXTO = (255, 255, 255)
COLOR_PROPIO = (255, 215, 80)  # la fila del jugador que mira la pantalla
COLOR_URGENTE = (240, 90, 90)
ANCHO_TABLA = 240
ALTO_FILA = 28
MARGEN = 12


def formato_reloj(segundos: float) -> str:
    """300 -> "5:00"; 9 -> "0:09"."""
    segundos = max(0, int(segundos))
    return f"{segundos // 60}:{segundos % 60:02d}"


def texto_reloj(info_partida: dict) -> str:
    estado = info_partida.get("estado", "esperando")
    if estado == "esperando":
        return "Esperando inicio"
    if estado == "finalizada":
        return "Fin"
    return formato_reloj(info_partida.get("tiempo_restante", 0))


def posiciones(jugadores: list[dict]) -> list[tuple[int, str, int, int]]:
    """(puesto, nombre, puntaje, jugador_id) de mayor a menor; los empates comparten puesto."""
    ordenados = sorted(jugadores, key=lambda j: (-j.get("puntaje", 0), j["jugador_id"]))
    filas: list[tuple[int, str, int, int]] = []
    for indice, jugador in enumerate(ordenados):
        puntaje = jugador.get("puntaje", 0)
        if filas and filas[-1][2] == puntaje:
            puesto = filas[-1][0]
        else:
            puesto = indice + 1
        nombre = jugador.get("nombre") or f"Jugador {jugador['jugador_id']}"
        filas.append((puesto, nombre, puntaje, jugador["jugador_id"]))
    return filas


class HudPartida:
    def __init__(self) -> None:
        self.fuente = pygame.font.Font(None, 28)
        self.fuente_reloj = pygame.font.Font(None, 44)

    def dibujar(self, screen: pygame.Surface, estado: dict, mi_id: int | None = None) -> None:
        info = estado.get("partida", {})
        self._dibujar_reloj(screen, info)
        self._dibujar_tabla(screen, estado.get("jugadores", []), info, mi_id)

    @staticmethod
    def _caja(screen: pygame.Surface, rect: pygame.Rect) -> None:
        """Fondo oscuro semitransparente para que se lea encima de la arena."""
        fondo = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(fondo, COLOR_FONDO, fondo.get_rect(), border_radius=10)
        screen.blit(fondo, rect.topleft)

    def _dibujar_reloj(self, screen: pygame.Surface, info: dict) -> None:
        en_curso = info.get("estado") == "en_curso"
        urgente = en_curso and info.get("tiempo_restante", 0) <= POCO_TIEMPO_S
        color = COLOR_URGENTE if urgente else COLOR_TEXTO
        imagen = self.fuente_reloj.render(texto_reloj(info), True, color)
        rect = imagen.get_rect(topleft=(MARGEN + 12, MARGEN + 8))
        self._caja(screen, rect.inflate(24, 16))
        screen.blit(imagen, rect)

    def _dibujar_tabla(
        self, screen: pygame.Surface, jugadores: list[dict], info: dict, mi_id: int | None
    ) -> None:
        filas = posiciones(jugadores)
        if not filas:
            return
        objetivo = info.get("puntaje_objetivo")
        titulo = f"Posiciones (meta {objetivo})" if objetivo else "Posiciones"
        alto = ALTO_FILA * (len(filas) + 1) + 8
        rect = pygame.Rect(screen.get_width() - ANCHO_TABLA - MARGEN, MARGEN, ANCHO_TABLA, alto)
        self._caja(screen, rect)
        y = rect.y + 6
        screen.blit(self.fuente.render(titulo, True, COLOR_TEXTO), (rect.x + 10, y))
        for puesto, nombre, puntaje, jugador_id in filas:
            y += ALTO_FILA
            color = COLOR_PROPIO if jugador_id == mi_id else COLOR_TEXTO
            fila = self.fuente.render(f"{puesto}. {nombre[:14]}", True, color)
            screen.blit(fila, (rect.x + 10, y))
            valor = self.fuente.render(str(puntaje), True, color)
            screen.blit(valor, valor.get_rect(topright=(rect.right - 10, y)))
