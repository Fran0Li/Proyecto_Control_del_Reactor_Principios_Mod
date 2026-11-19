"""Ceremonia de victoria al terminar la partida (US-18)."""

import asyncio
import os

import pygame
import pytest

from src.api_client import ApiError
from src.screens import ceremonia
from src.screens.arena import ESPERA_CEREMONIA_S, ArenaScreen
from src.screens.ceremonia import (
    CeremoniaScreen,
    Confeti,
    cantidad,
    orden_del_podio,
    sonido_de_fanfarria,
    titulo,
)

ANCHO, ALTO = 960, 640


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((ANCHO, ALTO))
    yield
    pygame.quit()


def jugador(jugador_id, nombre, puntaje, posicion):
    return {"jugador_id": jugador_id, "nombre": nombre, "puntaje": puntaje, "posicion": posicion}


POSICIONES = [
    jugador(2, "beto", 320, 1),
    jugador(1, "ana", 180, 2),
    jugador(3, "carla", 90, 3),
    jugador(4, "dani", 20, 4),
]
ESTADISTICAS = {
    "jugadores": [
        {
            **jugador(2, "beto", 320, 1),
            "acciones": 12,
            "penalizaciones": 1,
            "logros": [{"clave": "primera_victoria", "nombre": "Primera victoria"}],
            "record_personal": True,
        },
        {
            **jugador(1, "ana", 180, 2),
            "acciones": 7,
            "penalizaciones": 0,
            "logros": [],
            "record_personal": False,
        },
    ]
}


# lógica del podio


def test_el_podio_pone_al_primero_en_el_medio():
    assert [p["nombre"] for p in orden_del_podio(POSICIONES)] == ["ana", "beto", "carla"]


def test_con_dos_jugadores_el_podio_tiene_dos_escalones():
    assert [p["nombre"] for p in orden_del_podio(POSICIONES[:2])] == ["ana", "beto"]
    assert orden_del_podio(POSICIONES[:1]) == POSICIONES[:1]


def test_el_titulo_nombra_al_ganador_o_avisa_el_empate():
    assert titulo(POSICIONES) == "¡beto gana!"
    empate = [jugador(1, "ana", 50, 1), jugador(2, "beto", 50, 1)]
    assert titulo(empate) == "¡Empate!"
    assert titulo([]) == "Partida terminada"


def test_las_cantidades_usan_singular_y_plural():
    assert cantidad(1, "acción") == "1 acción"
    assert cantidad(4, "acción") == "4 acciones"
    assert cantidad(0, "penalización") == "0 penalizaciones"


def test_el_confeti_cae_y_vuelve_a_salir_por_arriba():
    confeti = Confeti(ANCHO, ALTO, cantidad=20)
    confeti.papeles[0][1] = ALTO - 1

    confeti.actualizar(1.0)

    assert confeti.papeles[0][1] <= 0  # salió por abajo y volvió a empezar arriba
    assert len(confeti.papeles) == 20


def test_la_fanfarria_se_arma_o_no_falla_sin_audio():
    sonido = sonido_de_fanfarria()
    assert sonido is None or sonido.get_length() > 0.5


# pantalla


def ceremonia_con(monkeypatch, respuestas):
    """`respuestas`: lo que devuelve /resultado en cada intento (un dict o un ApiError)."""
    llamadas = []

    async def obtener(partida_id, token):
        llamadas.append((partida_id, token))
        respuesta = respuestas[min(len(llamadas), len(respuestas)) - 1]
        if isinstance(respuesta, ApiError):
            raise respuesta
        return respuesta

    monkeypatch.setattr(ceremonia, "obtener_resultado", obtener)
    monkeypatch.setattr(ceremonia, "ESPERA_ENTRE_INTENTOS_S", 0)
    pantalla = CeremoniaScreen(ANCHO, ALTO)

    async def escenario():
        pantalla.preparar({"posiciones": POSICIONES, "motivo": "puntaje"}, 7, "token-ana")
        while pantalla.ocupada():
            await asyncio.sleep(0)

    asyncio.run(escenario())
    return pantalla, llamadas


def test_muestra_el_podio_y_carga_las_estadisticas(monkeypatch):
    pantalla, llamadas = ceremonia_con(monkeypatch, [ESTADISTICAS])

    assert llamadas == [(7, "token-ana")]
    assert pantalla.estadisticas == ESTADISTICAS
    assert pantalla.motivo == "Se alcanzó el puntaje objetivo"
    pantalla.update(1.0)
    pantalla.draw(pygame.display.get_surface())  # podio, trofeo, confeti y estadísticas


def test_si_el_resultado_se_esta_guardando_vuelve_a_intentar(monkeypatch):
    guardando = ApiError("La partida todavía no terminó", 409)
    pantalla, llamadas = ceremonia_con(monkeypatch, [guardando, guardando, ESTADISTICAS])

    assert len(llamadas) == 3
    assert pantalla.estadisticas == ESTADISTICAS


def test_si_falla_de_otra_forma_muestra_el_error_y_deja_el_podio(monkeypatch):
    pantalla, llamadas = ceremonia_con(monkeypatch, [ApiError("Sin conexión con el servidor")])

    assert len(llamadas) == 1
    assert pantalla.estadisticas is None
    assert pantalla.aviso == "Sin conexión con el servidor"
    pantalla.draw(pygame.display.get_surface())


def test_deja_de_intentar_despues_de_varios_409(monkeypatch):
    pantalla, llamadas = ceremonia_con(monkeypatch, [ApiError("todavía no", 409)])

    assert len(llamadas) == ceremonia.INTENTOS
    assert pantalla.aviso == "No se pudieron cargar las estadísticas"


def test_volver_lleva_al_lobby_con_el_boton_o_con_esc(monkeypatch):
    pantalla, _ = ceremonia_con(monkeypatch, [ESTADISTICAS])
    clic = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, pos=pantalla.boton_volver.rect.center, button=1
    )

    pantalla.handle_event(clic)
    assert pantalla.siguiente_pantalla == "lobby"

    pantalla.siguiente_pantalla = None
    pantalla.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert pantalla.siguiente_pantalla == "lobby"


# de la arena a la ceremonia


class PanelTerminado:
    def __init__(self):
        self.canal = None
        self.estado = None
        self.resultado = None


def test_la_arena_pasa_a_la_ceremonia_unos_segundos_despues_del_fin():
    ahora = [100.0]
    panel = PanelTerminado()
    arena = ArenaScreen(ANCHO, ALTO, reloj=lambda: ahora[0])
    arena.preparar(panel, "lobby")

    arena.update()
    assert arena.siguiente_pantalla is None  # todavía no terminó

    panel.resultado = {"tipo": "partida_finalizada", "posiciones": POSICIONES}
    arena.update()
    ahora[0] += ESPERA_CEREMONIA_S - 0.5
    arena.update()
    assert arena.siguiente_pantalla is None  # se ven las posiciones un momento

    ahora[0] += 1
    arena.update()
    assert arena.siguiente_pantalla == "ceremonia"
    assert not arena.activa
