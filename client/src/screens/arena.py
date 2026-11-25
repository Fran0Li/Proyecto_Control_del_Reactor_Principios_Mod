"""Pantalla de la arena: los jugadores (sprite por número), el reactor, las celdas y obstáculos.

Encima van el reloj y la tabla de posiciones (US-24). Cuando la partida termina (US-17) se pone
un cuadro con las posiciones finales y a los pocos segundos se pasa a la ceremonia (US-18).
"""

import time
from collections.abc import Callable

import pygame

from src import sesion, sprites
from src.config import CONTROL_PUERTO
from src.entrada import ControlesJugador, crear_fuentes
from src.screens.aviso_control import AvisoControl
from src.screens.componentes import boton_secundario
from src.screens.dibujo_fondo import dibujar_fondo
from src.screens.dibujo_guardianes import dibujar_guardianes
from src.screens.dibujo_jugadores import dibujar_jugador
from src.screens.dibujo_obstaculos import dibujar_obstaculos
from src.screens.dibujo_reactor import dibujar_reactor
from src.screens.hud_partida import HudPartida
from src.screens.panel_canal import PanelCanal
from src.screens.particulas import SistemaParticulas

BLANCO = (255, 255, 255)
ROJO = (220, 30, 30)
AMARILLO = (240, 190, 20)
RADIO_CELDA = 10  # el servidor usa el mismo radio para saber cuándo se recoge una celda
SPRITE_CELDA = "extra/TorreMagica_Futurista"
LADO_CELDA = 30  # el sprite es de 30 x 30 y se dibuja sin ampliar
SUAVIZADO = 0.35  # cuánto se acerca al punto nuevo en cada cuadro (el servidor manda ~20 por s)
# Caminando se avanzan unos 6 px por estado del servidor; un salto mayor es que lo mandaron a otro
# lugar (al iniciar la partida todos vuelven a su punto de inicio) y se dibuja allá de una vez.
SALTO_PX = 100
# Botón para volver al lobby antes de iniciar (modo práctica): en el celular no hay Esc
RECT_VOLVER = pygame.Rect(12, 72, 190, 38)
CONTROLES = ("arriba", "abajo", "izquierda", "derecha", "accion")
ESPERA_CEREMONIA_S = 3.0  # cuánto se ve el cuadro de posiciones antes de la ceremonia (US-18)
MOTIVOS = {
    "tiempo": "Se acabó el tiempo",
    "puntaje": "Alguien llegó al puntaje objetivo",
    "administrador": "Un administrador cerró la partida",
}


class ArenaScreen:
    def __init__(self, ancho: int, alto: int, reloj: Callable[[], float] = time.monotonic) -> None:
        self.ancho, self.alto = ancho, alto
        self._reloj = reloj
        self._terminada_en: float | None = None  # cuándo llegó el fin de la partida
        self.siguiente_pantalla: str | None = None
        self.activa = False
        self.panel: PanelCanal | None = None
        self.volver_a = "lobby"
        self.controles: ControlesJugador | None = None
        self.aviso_control = AvisoControl()
        self.visuales: dict[int, list[float]] = {}  # posición dibujada (suavizada)
        self.fuente_titulo = pygame.font.Font(None, 56)
        self.fuente = pygame.font.Font(None, 32)
        self.fuente_etiqueta = pygame.font.Font(None, 20)  # "J1" o "Vos" sobre cada jugador
        self.hud = HudPartida()  # reloj y tabla de posiciones (US-24)
        self.particulas = SistemaParticulas()  # chispas cuando un guardián alcanza a alguien
        self._estados_previos: dict[int, str | None] = {}
        self._ultimo_cuadro: float | None = None
        self.boton_volver = boton_secundario(RECT_VOLVER.copy(), "Volver al lobby")

    # ciclo de vida

    def preparar(self, panel: PanelCanal, volver_a: str) -> None:
        """La llama el ciclo principal justo antes de mostrar la arena."""
        self.cerrar()
        self.panel = panel
        self.volver_a = volver_a
        self.siguiente_pantalla = None
        if panel.canal is not None:
            fuentes = crear_fuentes(self.ancho, self.alto, CONTROL_PUERTO)
            # misma conexión que la vez anterior en la arena: el seq sigue desde donde quedó
            seq = getattr(panel, "seq_enviada", 0)
            self.controles = ControlesJugador(fuentes, panel.canal.enviar, seq_inicial=seq)
        self.aviso_control = AvisoControl()
        self._terminada_en = None
        self.activa = True

    def cerrar(self) -> None:
        if self.controles is not None:
            if self.panel is not None:
                self.panel.seq_enviada = self.controles.seq  # para la próxima vez en la arena
            self.controles.cerrar()
            self.controles = None
        self.activa = False
        self.visuales = {}
        self.particulas.vaciar()
        self._estados_previos = {}
        self._ultimo_cuadro = None

    def _salir(self) -> None:
        self._soltar_todo()
        self.siguiente_pantalla = self.volver_a
        self.cerrar()

    def _soltar_todo(self) -> None:
        """Al salir, el servidor no debe seguir moviendo al jugador con una tecla apretada."""
        if self.panel is None or self.panel.canal is None:
            return
        for control in CONTROLES:
            self.panel.canal.enviar(
                {"tipo": "entrada", "control": control, "estado": "liberado", "origen": "teclado"}
            )

    # eventos y actualización

    def en_practica(self) -> bool:
        """Antes de que el creador inicie la partida: se puede probar la arena, pero no cuenta."""
        estado = self.panel.estado if self.panel is not None else None
        if estado is None or getattr(self.panel, "resultado", None) is not None:
            return False
        return estado.get("partida", {}).get("estado", "esperando") == "esperando"

    def _toco_volver(self, event: pygame.event.Event) -> bool:
        if not self.activa or not self.en_practica():
            return False
        return self.boton_volver.fue_presionado(event)  # acepta dedo y mouse

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._salir()
        elif self._toco_volver(event):
            self._salir()
        elif self.controles is not None:
            self.controles.procesar(event)

    def update(self) -> None:
        if not self.activa or self.panel is None:
            return
        if self.controles is not None:
            self.controles.actualizar()
            control = self.controles.control_fisico()
            self.aviso_control.observar(control.estado if control is not None else None)
        if self.panel.estado is not None:
            self._acercar(self.panel.estado["jugadores"])
            self._detectar_golpes(self.panel.estado["jugadores"])
        ahora = self._reloj()
        if self._ultimo_cuadro is not None:
            self.particulas.actualizar(min(ahora - self._ultimo_cuadro, 0.1))
        self._ultimo_cuadro = ahora
        self._revisar_fin()

    def _detectar_golpes(self, jugadores: list[dict]) -> None:
        """Si un jugador pasa a "aturdido", un guardián lo acaba de alcanzar (US-15): chispas."""
        for jugador in jugadores:
            jugador_id = jugador["jugador_id"]
            antes = self._estados_previos.get(jugador_id, "sin_ver")
            ahora = jugador.get("estado")
            if ahora == "aturdido" and antes not in ("aturdido", "sin_ver"):
                x, y = self.visuales.get(jugador_id, [jugador["x"], jugador["y"]])
                self.particulas.impacto(x, y)
            self._estados_previos[jugador_id] = ahora

    def _revisar_fin(self) -> None:
        """Unos segundos después del fin de la partida se pasa a la ceremonia."""
        if getattr(self.panel, "resultado", None) is None:
            return
        if self._terminada_en is None:
            self._terminada_en = self._reloj()
        elif self._reloj() - self._terminada_en >= ESPERA_CEREMONIA_S:
            self._soltar_todo()
            self.cerrar()
            self.siguiente_pantalla = "ceremonia"

    def _acercar(self, jugadores: list[dict]) -> None:
        """Mueve lo dibujado hacia lo que dice el servidor, para que no avance a saltos."""
        presentes = set()
        for jugador in jugadores:
            jugador_id = jugador["jugador_id"]
            presentes.add(jugador_id)
            actual = self.visuales.get(jugador_id)
            if actual is None:
                self.visuales[jugador_id] = [float(jugador["x"]), float(jugador["y"])]
            elif abs(jugador["x"] - actual[0]) + abs(jugador["y"] - actual[1]) > SALTO_PX:
                actual[0], actual[1] = float(jugador["x"]), float(jugador["y"])
            else:
                actual[0] += (jugador["x"] - actual[0]) * SUAVIZADO
                actual[1] += (jugador["y"] - actual[1]) * SUAVIZADO
        for jugador_id in list(self.visuales):
            if jugador_id not in presentes:
                del self.visuales[jugador_id]

    # dibujo

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(BLANCO)
        estado = self.panel.estado if self.panel is not None else None
        if estado is not None:
            # la arena del servidor mide 960 x 540 y la ventana tiene 960 de ancho: se dibuja 1 a 1
            dibujar_fondo(screen, estado.get("escenario"))
            dibujar_obstaculos(screen, estado["arena"].get("obstaculos", []))
            reactor = estado["arena"].get("reactor")
            if reactor is not None:
                energia = estado.get("reactor", {})
                dibujar_reactor(
                    screen,
                    reactor,
                    energia.get("energia"),
                    energia.get("capacidad"),
                    self._reloj(),
                )
            celda_sprite = sprites.cargar(SPRITE_CELDA, (LADO_CELDA, LADO_CELDA))
            for celda in estado["arena"].get("celdas", []):
                centro_celda = (celda["x"], celda["y"])
                if celda_sprite is not None:
                    screen.blit(celda_sprite, celda_sprite.get_rect(center=centro_celda))
                else:
                    pygame.draw.circle(screen, AMARILLO, centro_celda, RADIO_CELDA)
            dibujar_guardianes(screen, estado.get("guardianes", []))
            propio = sesion.jugador_id()
            for jugador in estado["jugadores"]:
                x, y = self.visuales.get(jugador["jugador_id"], [jugador["x"], jugador["y"]])
                dibujar_jugador(
                    screen,
                    x,
                    y,
                    estado["arena"]["radio"],
                    numero=jugador.get("numero"),
                    estado=jugador.get("estado"),
                    propio=jugador["jugador_id"] == propio,
                    fuente=self.fuente_etiqueta,
                )
            self.particulas.dibujar(screen)
            self.hud.dibujar(screen, estado, sesion.jugador_id())
            if self.en_practica():
                self.boton_volver.draw(screen)
        if self.controles is not None:
            self.controles.dibujar(screen)  # botones táctiles, solo en el navegador
        self.aviso_control.dibujar(screen)  # estado del control físico (US-26)
        resultado = getattr(self.panel, "resultado", None)
        if resultado is not None:
            self._dibujar_resultado(screen, resultado)

    def _dibujar_resultado(self, screen: pygame.Surface, resultado: dict) -> None:
        velo = pygame.Surface((self.ancho, self.alto), pygame.SRCALPHA)
        velo.fill((0, 0, 0, 170))
        screen.blit(velo, (0, 0))
        centro_x = self.ancho // 2
        lineas = [
            (self.fuente_titulo, "PARTIDA TERMINADA"),
            (self.fuente, MOTIVOS.get(resultado.get("motivo"), "")),
        ]
        for jugador in resultado.get("posiciones", []):
            nombre = jugador["nombre"] or f"Jugador {jugador['jugador_id']}"
            fila = f"{jugador['posicion']}.  {nombre}  -  {jugador['puntaje']}"
            lineas.append((self.fuente, fila))
        lineas.append((self.fuente, "La ceremonia empieza en un momento..."))
        y = self.alto // 2 - 30 * len(lineas)
        for fuente, texto in lineas:
            imagen = fuente.render(texto, True, BLANCO)
            screen.blit(imagen, imagen.get_rect(center=(centro_x, y)))
            y += 50 if fuente is self.fuente_titulo else 38