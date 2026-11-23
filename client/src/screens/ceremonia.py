"""Ceremonia de victoria al terminar la partida (US-18).

El podio sale del aviso `partida_finalizada` que llega por el canal, así se ve apenas termina.
Las estadísticas (acciones, penalizaciones, logros y récords) se piden después a
`GET /partidas/{id}/resultado`; si el servidor todavía está guardando el resultado responde 409 y
se vuelve a intentar un momento después.
"""

import array
import asyncio
import math
import random

import pygame

from src.api_client import ApiError, obtener_resultado
from src.screens.componentes import Boton

COLOR_FONDO = (12, 16, 32)
COLOR_TITULO = (255, 215, 80)
COLOR_TEXTO = (235, 235, 245)
COLOR_SUAVE = (150, 160, 190)
COLOR_RECORD = (90, 220, 130)
COLORES_PODIO = {1: (230, 180, 40), 2: (180, 185, 200), 3: (190, 120, 60)}
COLORES_CONFETI = [(240, 80, 80), (80, 200, 255), (255, 215, 80), (90, 220, 130), (200, 120, 240)]
ALTURAS_PODIO = {1: 130, 2: 95, 3: 70}
ANCHO_ESCALON = 170
CANTIDAD_CONFETI = 120
INTENTOS = 10  # para pedir el resultado mientras el servidor termina de guardarlo
ESPERA_ENTRE_INTENTOS_S = 0.5
MOTIVOS = {
    "tiempo": "Se acabó el tiempo",
    "puntaje": "Se alcanzó el puntaje objetivo",
    "administrador": "Un administrador cerró la partida",
}


def orden_del_podio(posiciones: list[dict]) -> list[dict]:
    """Los tres primeros en el orden en que se dibujan: segundo, primero y tercero.

    Con empates puede haber dos primeros: van uno al lado del otro con la altura de su puesto.
    """
    tres = sorted(posiciones, key=lambda p: (p["posicion"], p["jugador_id"]))[:3]
    if len(tres) < 2:
        return tres
    if len(tres) == 2:
        return [tres[1], tres[0]]
    return [tres[1], tres[0], tres[2]]


def cantidad(numero: int, palabra: str) -> str:
    """cantidad(1, "acción") -> "1 acción"; cantidad(3, "acción") -> "3 acciones"."""
    if numero == 1:
        return f"1 {palabra}"
    plural = palabra[:-4] + "ciones" if palabra.endswith("ción") else palabra + "s"
    return f"{numero} {plural}"


def titulo(posiciones: list[dict]) -> str:
    primeros = [p for p in posiciones if p["posicion"] == 1]
    if len(primeros) == 1:
        return f"¡{primeros[0]['nombre']} gana!"
    return "¡Empate!" if primeros else "Partida terminada"


class Confeti:
    """Papelitos que caen y vuelven a salir por arriba."""

    def __init__(self, ancho: int, alto: int, cantidad: int = CANTIDAD_CONFETI) -> None:
        self.ancho, self.alto = ancho, alto
        self.papeles = [self._nuevo(arriba=False) for _ in range(cantidad)]

    def _nuevo(self, arriba: bool = True) -> list:
        y = random.uniform(-40, 0) if arriba else random.uniform(-self.alto, self.alto)
        # x, y, velocidad, fase del vaivén, color
        return [
            random.uniform(0, self.ancho),
            y,
            random.uniform(60, 140),
            random.uniform(0, math.tau),
            random.choice(COLORES_CONFETI),
        ]

    def actualizar(self, dt: float) -> None:
        for i, papel in enumerate(self.papeles):
            papel[1] += papel[2] * dt
            papel[3] += 4 * dt
            if papel[1] > self.alto:
                self.papeles[i] = self._nuevo()

    def dibujar(self, screen: pygame.Surface) -> None:
        for x, y, _, fase, color in self.papeles:
            ancho = 3 + 3 * abs(math.sin(fase))  # parece que gira
            pygame.draw.rect(screen, color, (x + 8 * math.sin(fase), y, ancho, 9))


def sonido_de_fanfarria() -> pygame.mixer.Sound | None:
    """Cuatro notas que suben (do, mi, sol, do). Sin audio disponible, no suena y ya."""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        frecuencia, _, canales = pygame.mixer.get_init()
        muestras = array.array("h")
        for nota, duracion in ((523, 0.15), (659, 0.15), (784, 0.15), (1047, 0.45)):
            total = int(frecuencia * duracion)
            for i in range(total):
                caida = 1 - i / total  # cada nota se apaga suave
                valor = int(9000 * caida * math.sin(math.tau * nota * i / frecuencia))
                muestras.extend([valor] * canales)
        return pygame.mixer.Sound(buffer=muestras.tobytes())
    except (pygame.error, TypeError, ValueError):
        return None


class CeremoniaScreen:
    def __init__(self, ancho: int, alto: int) -> None:
        self.ancho, self.alto = ancho, alto
        self.centro_x = ancho // 2
        self.siguiente_pantalla: str | None = None
        self.fuente_titulo = pygame.font.Font(None, 72)
        self.fuente = pygame.font.Font(None, 30)
        self.fuente_chica = pygame.font.Font(None, 24)
        self.boton_volver = Boton(
            pygame.Rect(self.centro_x - 130, alto - 70, 260, 48), "Volver al lobby"
        )
        self.posiciones: list[dict] = []
        self.motivo = ""
        self.estadisticas: dict | None = None  # lo que devuelve /resultado
        self.aviso = ""
        self.confeti = Confeti(ancho, alto)
        self.tiempo = 0.0
        self._tarea: asyncio.Task | None = None

    def preparar(self, resultado: dict, partida_id: int, token: str) -> None:
        """La llama el ciclo principal con el aviso de fin de partida que llegó por el canal."""
        self.siguiente_pantalla = None
        self.posiciones = resultado.get("posiciones", [])
        self.motivo = MOTIVOS.get(resultado.get("motivo"), "")
        self.estadisticas = None
        self.aviso = "Cargando estadísticas..."
        self.confeti = Confeti(self.ancho, self.alto)
        self.tiempo = 0.0
        fanfarria = sonido_de_fanfarria()
        if fanfarria is not None:
            fanfarria.play()
        self._tarea = asyncio.create_task(self._cargar(partida_id, token))

    async def _cargar(self, partida_id: int, token: str) -> None:
        for _ in range(INTENTOS):
            try:
                self.estadisticas = await obtener_resultado(partida_id, token)
            except ApiError as error:
                if error.estado != 409:
                    self.aviso = str(error)
                    return
                await asyncio.sleep(ESPERA_ENTRE_INTENTOS_S)  # todavía se está guardando
            else:
                self.aviso = ""
                return
        self.aviso = "No se pudieron cargar las estadísticas"

    def ocupada(self) -> bool:
        return self._tarea is not None and not self._tarea.done()

    def handle_event(self, event: pygame.event.Event) -> None:
        escape = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        if escape or self.boton_volver.fue_presionado(event):
            self.siguiente_pantalla = "lobby"

    def update(self, dt: float = 1 / 30) -> None:
        self.tiempo += dt
        self.confeti.actualizar(dt)

    # dibujo

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(COLOR_FONDO)
        self.confeti.dibujar(screen)
        self._texto(screen, self.fuente_titulo, titulo(self.posiciones), COLOR_TITULO, 50)
        self._texto(screen, self.fuente, self.motivo, COLOR_SUAVE, 88)
        base_y = 350
        orden = orden_del_podio(self.posiciones)
        inicio_x = self.centro_x - len(orden) * ANCHO_ESCALON // 2
        for i, jugador in enumerate(orden):
            self._escalon(screen, jugador, inicio_x + i * ANCHO_ESCALON, base_y)
        self._dibujar_estadisticas(screen, base_y + 20)
        self.boton_volver.draw(screen)

    def _texto(self, screen, fuente, texto, color, y, x=None) -> None:
        imagen = fuente.render(texto, True, color)
        screen.blit(imagen, imagen.get_rect(center=(self.centro_x if x is None else x, y)))

    def _escalon(self, screen: pygame.Surface, jugador: dict, x: int, base_y: int) -> None:
        puesto = jugador["posicion"]
        alto = ALTURAS_PODIO.get(puesto, 60)
        # el escalón sube desde el piso en el primer segundo
        alto_visible = int(alto * min(1.0, self.tiempo / 0.8))
        rect = pygame.Rect(x + 10, base_y - alto_visible, ANCHO_ESCALON - 20, alto_visible)
        pygame.draw.rect(screen, COLORES_PODIO.get(puesto, COLOR_SUAVE), rect, border_radius=6)
        centro = rect.centerx
        if alto_visible > 30:
            self._texto(screen, self.fuente_titulo, str(puesto), COLOR_FONDO, rect.y + 32, centro)
        self._texto(screen, self.fuente, jugador["nombre"], COLOR_TEXTO, rect.y - 40, centro)
        self._texto(
            screen, self.fuente_chica, f"{jugador['puntaje']} pts", COLOR_SUAVE, rect.y - 18, centro
        )
        if puesto == 1:
            self._trofeo(screen, centro, rect.y - 95)

    def _trofeo(self, screen: pygame.Surface, x: int, y: int) -> None:
        brillo = 20 * math.sin(self.tiempo * 4)  # titila un poco
        oro = (235, int(190 + brillo), 50)
        pygame.draw.polygon(
            screen, oro, [(x - 22, y - 20), (x + 22, y - 20), (x + 12, y + 12), (x - 12, y + 12)]
        )  # copa
        pygame.draw.circle(screen, oro, (x - 22, y - 8), 9, 3)  # asas
        pygame.draw.circle(screen, oro, (x + 22, y - 8), 9, 3)
        pygame.draw.rect(screen, oro, (x - 4, y + 12, 8, 12))  # pie
        pygame.draw.rect(screen, oro, (x - 16, y + 24, 32, 7), border_radius=2)

    def _dibujar_estadisticas(self, screen: pygame.Surface, y: int) -> None:
        if self.estadisticas is None:
            self._texto(screen, self.fuente_chica, self.aviso, COLOR_SUAVE, y + 20)
            return
        for jugador in self.estadisticas["jugadores"][:4]:
            y += 26
            puesto = jugador["posicion"] or "-"
            linea = (
                f"{puesto}. {jugador['nombre']}   {jugador['puntaje']} pts   "
                f"{cantidad(jugador['acciones'], 'acción')}   "
                f"{cantidad(jugador['penalizaciones'], 'penalización')}"
            )
            self._texto(screen, self.fuente_chica, linea, COLOR_TEXTO, y)
            extras = [logro["nombre"] for logro in jugador["logros"]]
            if jugador["record_personal"]:
                extras.insert(0, "¡Récord personal!")
            if extras:
                y += 20
                self._texto(screen, self.fuente_chica, "  ·  ".join(extras), COLOR_RECORD, y)
