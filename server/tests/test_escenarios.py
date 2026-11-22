"""Escenarios (US-09): que cada mapa sea jugable, justo y distinto de los demás."""

import asyncio
import math
from collections import deque

import pytest

from app.realtime.arena import ALTO_ARENA, ANCHO_ARENA, PUNTOS_DE_INICIO
from app.realtime.celdas import RADIO_CELDA
from app.realtime.escenarios import (
    ESCENARIOS,
    NOMBRES_ESCENARIOS,
    EscenarioDesconocidoError,
    crear_escenario,
)
from app.realtime.gestor_motores import GestorMotores
from app.realtime.motor_partida import MotorPartida
from app.realtime.obstaculos import (
    BARRERA,
    BARRERA_MOVIL,
    PUERTA,
    TRAMPA,
    VELOCIDAD_BARRERA_MOVIL,
    posicion_en,
    toca,
)
from app.services.partida_factory import ESCENARIOS as ESCENARIOS_DE_LA_FACTORY

todos = pytest.mark.parametrize("nombre", NOMBRES_ESCENARIOS)

HOLGURA_REACTOR = 20  # espacio libre alrededor del reactor, además de su radio
PASO = 15  # tamaño de la cuadrícula con la que se revisa que haya camino


def test_estan_los_cinco_escenarios_del_enunciado():
    assert set(NOMBRES_ESCENARIOS) == {
        "laboratorio",
        "estacion_espacial",
        "planta_industrial",
        "centro_investigacion",
        "complejo_militar",
    }


def test_la_factory_de_partidas_usa_los_mismos_nombres():
    assert tuple(ESCENARIOS_DE_LA_FACTORY) == NOMBRES_ESCENARIOS


def test_un_escenario_desconocido_se_rechaza():
    with pytest.raises(EscenarioDesconocidoError):
        crear_escenario("la_luna")


@todos
def test_cada_llamada_devuelve_objetos_nuevos(nombre):
    arena_1, guardianes_1 = crear_escenario(nombre)
    arena_2, guardianes_2 = crear_escenario(nombre)
    assert arena_1 is not arena_2
    assert arena_1.obstaculos is not arena_2.obstaculos
    for uno, otro in zip(guardianes_1, guardianes_2, strict=True):
        assert uno is not otro
        assert uno.estrategia is not otro.estrategia


@todos
def test_el_reactor_queda_al_centro(nombre):
    arena, _ = crear_escenario(nombre)
    assert (arena.reactor.x, arena.reactor.y) == (ANCHO_ARENA / 2, ALTO_ARENA / 2)


@todos
def test_todo_obstaculo_queda_dentro_de_la_arena(nombre):
    arena, _ = crear_escenario(nombre)
    for o in arena.obstaculos:
        assert o.x >= 0 and o.y >= 0
        assert o.x + o.ancho <= ANCHO_ARENA
        assert o.y + o.alto <= ALTO_ARENA


@todos
def test_ningun_obstaculo_toca_el_reactor(nombre):
    arena, _ = crear_escenario(nombre)
    libre = arena.reactor.radio + arena.radio_jugador + HOLGURA_REACTOR
    for o in arena.obstaculos:
        punto_x = min(max(arena.reactor.x, o.x), o.x + o.ancho)
        punto_y = min(max(arena.reactor.y, o.y), o.y + o.alto)
        assert math.hypot(arena.reactor.x - punto_x, arena.reactor.y - punto_y) > libre


@todos
def test_los_cuatro_puntos_de_inicio_estan_libres(nombre):
    arena, _ = crear_escenario(nombre)
    for x, y in PUNTOS_DE_INICIO:
        for o in arena.obstaculos:
            assert not toca(x, y, arena.radio_jugador * 2, o)  # con margen para no nacer pegado


@todos
def test_el_mapa_es_simetrico(nombre):
    """Si no, un jugador tendría una esquina mejor que otra."""
    arena, _ = crear_escenario(nombre)
    reales = {(o.x, o.y, o.ancho, o.alto, o.tipo) for o in arena.obstaculos}
    for o in arena.obstaculos:
        espejo_x = (ANCHO_ARENA - o.x - o.ancho, o.y, o.ancho, o.alto, o.tipo)
        espejo_y = (o.x, ALTO_ARENA - o.y - o.alto, o.ancho, o.alto, o.tipo)
        assert espejo_x in reales
        assert espejo_y in reales


@todos
def test_hay_ocho_celdas_y_ninguna_dentro_de_un_obstaculo(nombre):
    arena, _ = crear_escenario(nombre)
    assert len(arena.celdas) == 8
    assert len({c.id for c in arena.celdas}) == 8
    for celda in arena.celdas:
        assert all(not toca(celda.x, celda.y, RADIO_CELDA, o) for o in arena.obstaculos)


@todos
def test_toda_celda_vale_diez_puntos(nombre):
    """CU-10 del ERS: la celda otorga 10 puntos."""
    arena, _ = crear_escenario(nombre)
    assert {c.valor for c in arena.celdas} == {10}


@todos
def test_ninguna_celda_toca_el_reactor(nombre):
    arena, _ = crear_escenario(nombre)
    for celda in arena.celdas:
        distancia = math.hypot(celda.x - arena.reactor.x, celda.y - arena.reactor.y)
        assert distancia > arena.reactor.radio + RADIO_CELDA


@todos
def test_ningun_guardian_nace_dentro_de_un_obstaculo(nombre):
    arena, guardianes = crear_escenario(nombre)
    assert guardianes
    for g in guardianes:
        assert 0 <= g.x <= ANCHO_ARENA and 0 <= g.y <= ALTO_ARENA
        assert all(not toca(g.x, g.y, g.radio, o) for o in arena.obstaculos)


@todos
def test_los_guardianes_no_se_meten_en_los_obstaculos_al_moverse(nombre):
    """Se mueve cada guardián 40 s de partida y se revisa que nunca pise una pared."""
    arena, guardianes = crear_escenario(nombre)
    paredes = [o for o in arena.obstaculos if o.tipo in (BARRERA, PUERTA)]
    for _ in range(800):  # 800 ticks de 50 ms
        for g in guardianes:
            g.mover(0.05, [])
            assert all(not toca(g.x, g.y, g.radio, o) for o in paredes)


def _libre(arena, x, y):
    if not (arena.radio_jugador <= x <= ANCHO_ARENA - arena.radio_jugador):
        return False
    if not (arena.radio_jugador <= y <= ALTO_ARENA - arena.radio_jugador):
        return False
    # las puertas se abren solas, así que solo las barreras cierran el camino para siempre
    barreras = [o for o in arena.obstaculos if o.tipo == BARRERA]
    return all(not toca(x, y, arena.radio_jugador, o) for o in barreras)


def _alcanzables(arena):
    """Casillas a las que llega un jugador que parte del primer punto de inicio."""
    inicio = tuple(PUNTOS_DE_INICIO[0])
    vistos = {inicio}
    pendientes = deque([inicio])
    while pendientes:
        x, y = pendientes.popleft()
        for dx, dy in ((PASO, 0), (-PASO, 0), (0, PASO), (0, -PASO)):
            vecino = (x + dx, y + dy)
            if vecino not in vistos and _libre(arena, *vecino):
                vistos.add(vecino)
                pendientes.append(vecino)
    return vistos


@todos
def test_siempre_hay_camino_a_los_otros_puntos_de_inicio_y_al_reactor(nombre):
    arena, _ = crear_escenario(nombre)
    alcanzables = _alcanzables(arena)
    destinos = [tuple(p) for p in PUNTOS_DE_INICIO[1:]]
    destinos.append((arena.reactor.x - arena.reactor.radio - arena.radio_jugador, arena.reactor.y))
    for destino in destinos:
        assert destino in alcanzables


@todos
def test_todas_las_celdas_se_pueden_alcanzar(nombre):
    arena, _ = crear_escenario(nombre)
    alcanzables = _alcanzables(arena)
    for celda in arena.celdas:
        cerca = any(
            math.hypot(x - celda.x, y - celda.y) <= arena.radio_jugador + RADIO_CELDA
            for x, y in alcanzables
        )
        assert cerca


@todos
def test_los_tipos_de_obstaculo_son_los_conocidos(nombre):
    arena, _ = crear_escenario(nombre)
    assert arena.obstaculos
    assert {o.tipo for o in arena.obstaculos} <= {BARRERA, TRAMPA, PUERTA, BARRERA_MOVIL}


def _posiciones_de_las_barreras_moviles(arena):
    """Cada barrera móvil en 200 momentos de su recorrido (de ida y vuelta)."""
    moviles = [o for o in arena.obstaculos if o.tipo == BARRERA_MOVIL]
    for o in moviles:
        ciclo = 2 * math.hypot(o.destino_x - o.x, o.destino_y - o.y) / VELOCIDAD_BARRERA_MOVIL
        for paso in range(201):
            yield posicion_en(o, ciclo * paso / 200, VELOCIDAD_BARRERA_MOVIL)


def test_laboratorio_y_centro_de_investigacion_tienen_barreras_moviles():
    for nombre in ("laboratorio", "centro_investigacion"):
        arena, _ = crear_escenario(nombre)
        moviles = [o for o in arena.obstaculos if o.tipo == BARRERA_MOVIL]
        assert len(moviles) == 4  # una por cuadrante
        assert all(o.destino_x is not None and o.destino_y is not None for o in moviles)


@todos
def test_las_barreras_moviles_nunca_salen_de_la_arena(nombre):
    arena, _ = crear_escenario(nombre)
    for o in _posiciones_de_las_barreras_moviles(arena):
        assert o.x >= 0 and o.y >= 0
        assert o.x + o.ancho <= ANCHO_ARENA
        assert o.y + o.alto <= ALTO_ARENA


@todos
def test_las_barreras_moviles_nunca_tocan_el_reactor(nombre):
    arena, _ = crear_escenario(nombre)
    libre = arena.reactor.radio + arena.radio_jugador + HOLGURA_REACTOR
    for o in _posiciones_de_las_barreras_moviles(arena):
        punto_x = min(max(arena.reactor.x, o.x), o.x + o.ancho)
        punto_y = min(max(arena.reactor.y, o.y), o.y + o.alto)
        assert math.hypot(arena.reactor.x - punto_x, arena.reactor.y - punto_y) > libre


@todos
def test_las_barreras_moviles_nunca_tapan_un_punto_de_inicio_ni_una_celda(nombre):
    arena, _ = crear_escenario(nombre)
    for o in _posiciones_de_las_barreras_moviles(arena):
        for x, y in PUNTOS_DE_INICIO:
            assert not toca(x, y, arena.radio_jugador * 2, o)
        for celda in arena.celdas:
            assert not toca(celda.x, celda.y, RADIO_CELDA, o)


@todos
def test_las_barreras_moviles_no_se_cruzan_con_otras_paredes(nombre):
    arena, _ = crear_escenario(nombre)
    paredes = [o for o in arena.obstaculos if o.tipo in (BARRERA, PUERTA)]
    for m in _posiciones_de_las_barreras_moviles(arena):
        for p in paredes:
            separadas = (
                m.x + m.ancho <= p.x
                or p.x + p.ancho <= m.x
                or m.y + m.alto <= p.y
                or p.y + p.alto <= m.y
            )
            assert separadas


@todos
def test_el_recorrido_de_la_barrera_movil_es_simetrico(nombre):
    arena, _ = crear_escenario(nombre)
    moviles = [o for o in arena.obstaculos if o.tipo == BARRERA_MOVIL]
    recorridos = {(o.x, o.y, o.destino_x, o.destino_y, o.ancho, o.alto) for o in moviles}
    for o in moviles:
        espejo_x = (
            ANCHO_ARENA - o.x - o.ancho,
            o.y,
            ANCHO_ARENA - o.destino_x - o.ancho,
            o.destino_y,
            o.ancho,
            o.alto,
        )
        espejo_y = (
            o.x,
            ALTO_ARENA - o.y - o.alto,
            o.destino_x,
            ALTO_ARENA - o.destino_y - o.alto,
            o.ancho,
            o.alto,
        )
        assert espejo_x in recorridos
        assert espejo_y in recorridos


def test_el_motor_manda_la_barrera_movil_en_otro_lugar_con_el_tiempo():
    arena, guardianes = crear_escenario("laboratorio")
    motor = MotorPartida(1, arena=arena, guardianes=guardianes, escenario="laboratorio")
    antes = [o for o in motor.estado()["arena"]["obstaculos"] if o["tipo"] == BARRERA_MOVIL]

    async def correr():
        for _ in range(40):  # 2 s de partida
            await motor.tick()

    asyncio.run(correr())
    despues = [o for o in motor.estado()["arena"]["obstaculos"] if o["tipo"] == BARRERA_MOVIL]
    assert len(antes) == len(despues) == 4
    assert [o["x"] for o in antes] != [o["x"] for o in despues]


def test_los_mapas_se_distinguen_entre_si():
    firmas = set()
    for nombre in NOMBRES_ESCENARIOS:
        arena, guardianes = crear_escenario(nombre)
        firmas.add(
            (
                tuple(sorted((o.x, o.y, o.ancho, o.alto, o.tipo) for o in arena.obstaculos)),
                tuple(sorted((g.x, g.y) for g in guardianes)),
            )
        )
    assert len(firmas) == len(NOMBRES_ESCENARIOS)


def test_la_estacion_espacial_tiene_puertas_y_la_planta_industrial_trampas():
    estacion, _ = crear_escenario("estacion_espacial")
    planta, _ = crear_escenario("planta_industrial")
    assert any(o.tipo == PUERTA for o in estacion.obstaculos)
    assert any(o.tipo == TRAMPA for o in planta.obstaculos)


def test_el_centro_de_investigacion_y_el_complejo_tienen_guardianes_que_persiguen():
    for nombre, cantidad in (("centro_investigacion", 2), ("complejo_militar", 3)):
        _, guardianes = crear_escenario(nombre)
        assert len(guardianes) == cantidad


# conexión con el motor y el gestor


@todos
def test_el_motor_manda_el_escenario_el_mapa_y_los_guardianes(nombre):
    arena, guardianes = crear_escenario(nombre)
    motor = MotorPartida(1, arena=arena, guardianes=guardianes, escenario=nombre)
    estado = motor.estado()
    assert estado["escenario"] == nombre
    assert len(estado["arena"]["obstaculos"]) == len(arena.obstaculos)
    assert len(estado["arena"]["celdas"]) == 8
    assert len(estado["guardianes"]) == len(guardianes)


def test_sin_escenario_el_estado_no_trae_el_campo():
    assert "escenario" not in MotorPartida(1).estado()


@todos
def test_el_gestor_crea_el_motor_con_el_escenario_pedido(nombre):
    gestor = GestorMotores(canales=None, fabrica_sesiones=None)

    async def probar():
        motor = gestor.obtener(7, nombre)
        try:
            assert motor.escenario == nombre
            assert motor.estado()["guardianes"]
            # pedirlo otra vez devuelve el mismo motor, no uno nuevo
            assert gestor.obtener(7, "laboratorio") is motor
        finally:
            await motor.detener()
            gestor.limpiar()

    asyncio.run(probar())


def test_el_gestor_rechaza_un_escenario_desconocido():
    gestor = GestorMotores(canales=None, fabrica_sesiones=None)
    with pytest.raises(EscenarioDesconocidoError):
        gestor.obtener(8, "la_luna")


def test_dos_partidas_del_mismo_escenario_no_comparten_guardianes():
    uno = crear_escenario("planta_industrial")[1]
    otro = crear_escenario("planta_industrial")[1]
    uno[0].x = 999
    assert otro[0].x != 999


def test_los_escenarios_estan_registrados_por_su_nombre():
    for nombre, escenario in ESCENARIOS.items():
        assert escenario.nombre == nombre