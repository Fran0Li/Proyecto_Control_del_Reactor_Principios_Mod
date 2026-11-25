"""Pruebas de los eventos especiales (US-16): puntos dobles e invasión. Sin red ni base de datos."""

import asyncio
import itertools
import math
import random

import pytest

from app.realtime.arena import Arena, Celda, Obstaculo, Reactor
from app.realtime.connection_manager import ConnectionManager
from app.realtime.eventos import (
    ACCION_REALIZADA,
    ESTADO_ACTUALIZADO,
    EVENTO_ESPECIAL_FINALIZADO,
    EVENTO_ESPECIAL_INICIADO,
    JUGADOR_PENALIZADO,
)
from app.realtime.eventos_especiales import (
    ID_PRIMER_INVASOR,
    INVASORES,
    FabricaEventos,
    Invasion,
    ProgramadorEventos,
    PuntosDobles,
)
from app.realtime.gestor_motores import GestorMotores
from app.realtime.guardianes import RADIO_GUARDIAN, Guardian, Patrulla
from app.realtime.motor_partida import CICLO_S, MotorPartida
from app.realtime.obstaculos import toca
from app.realtime.registro_eventos import TIPOS_GUARDADOS

REACTOR = Reactor(480, 270, 40)
RADIO_JUGADOR = 20


class ObservadorConReloj:
    """Guarda cada evento junto con el segundo de la partida en que llegó."""

    def __init__(self, motor):
        self.motor = motor
        self.eventos = []

    async def al_evento(self, evento):
        self.eventos.append((evento.tipo, evento.datos, self.motor.tiempo))

    def de_tipo(self, tipo):
        return [(datos, tiempo) for t, datos, tiempo in self.eventos if t == tipo]


class FabricaFija:
    """Da los eventos en el orden pedido, para no depender del azar."""

    def __init__(self, *claves, semilla=0):
        self._real = FabricaEventos(random.Random(semilla))
        self._ciclo = itertools.cycle(claves)

    def crear_al_azar(self, excluir=None):
        return self._real.crear(next(self._ciclo))


def avanzar(motor, ticks):
    async def correr():
        for _ in range(ticks):
            await motor.tick()

    asyncio.run(correr())


def ticks_para(segundos):
    return round(segundos / CICLO_S)


def arena_de_prueba(inicios, obstaculos=(), celdas=()):
    return Arena(
        reactor=REACTOR,
        puntos_inicio=tuple(inicios),
        obstaculos=list(obstaculos),
        celdas=list(celdas),
    )


def motor_con_eventos(
    *claves,
    inicios=((100, 100),),
    obstaculos=(),
    celdas=(),
    guardianes=None,
    primer=1.0,
    duracion=3.0,
    espera=2.0,
    semilla=0,
):
    """Una partida ya iniciada donde el primer evento sale a los `primer` segundos."""
    programador = ProgramadorEventos(
        fabrica=FabricaFija(*claves, semilla=semilla),
        azar=random.Random(semilla),
        primer_evento_s=primer,
        espera_minima_s=espera,
        espera_maxima_s=espera,
        duracion_s=duracion,
    )
    motor = MotorPartida(
        1,
        arena=arena_de_prueba(inicios, obstaculos, celdas),
        guardianes=guardianes,
        eventos=programador,
    )
    for numero in range(1, len(inicios) + 1):
        motor.agregar_jugador(numero)
    motor.iniciar_partida(300, 500)
    return motor


def motor_real(semilla=0, jugadores=1):
    """Una partida ya iniciada con los tiempos de verdad (30 s, 10 s, 30 a 45 s)."""
    programador = ProgramadorEventos(azar=random.Random(semilla))
    inicios = ((100, 100), (860, 440))[:jugadores]
    motor = MotorPartida(1, arena=arena_de_prueba(inicios), eventos=programador)
    for numero in range(1, jugadores + 1):
        motor.agregar_jugador(numero)
    motor.iniciar_partida(300, 500)
    return motor


def evento_actual(motor):
    return motor.estado()["partida"].get("evento")


def puntaje(motor, jugador_id=1):
    return next(j["puntaje"] for j in motor.estado()["jugadores"] if j["jugador_id"] == jugador_id)


def guardianes_del_estado(motor):
    return motor.estado()["guardianes"]


class TestFabrica:
    def test_conoce_los_dos_eventos(self):
        assert set(FabricaEventos().claves) == {"puntos_dobles", "invasion"}

    def test_crea_cada_evento_con_su_nombre(self):
        fabrica = FabricaEventos()
        assert fabrica.crear("puntos_dobles").nombre == "Puntos dobles"
        assert fabrica.crear("invasion").nombre == "Invasión"

    def test_una_clave_desconocida_falla(self):
        with pytest.raises(ValueError):
            FabricaEventos().crear("terremoto")

    def test_al_azar_no_repite_el_que_se_excluye(self):
        fabrica = FabricaEventos(random.Random(5))
        assert all(
            fabrica.crear_al_azar(excluir="invasion").clave == "puntos_dobles" for _ in range(30)
        )
        assert all(
            fabrica.crear_al_azar(excluir="puntos_dobles").clave == "invasion" for _ in range(30)
        )

    def test_al_azar_salen_los_dos(self):
        fabrica = FabricaEventos(random.Random(5))
        assert {fabrica.crear_al_azar().clave for _ in range(40)} == {"puntos_dobles", "invasion"}

    def test_cada_llamada_crea_un_evento_nuevo(self):
        fabrica = FabricaEventos()
        assert fabrica.crear("invasion") is not fabrica.crear("invasion")


class TestTiempos:
    def test_sin_programador_no_hay_eventos(self):
        motor = MotorPartida(1, arena=arena_de_prueba(((100, 100),)))
        motor.agregar_jugador(1)
        motor.iniciar_partida(300, 500)
        avanzar(motor, ticks_para(60))
        assert "evento" not in motor.estado()["partida"]

    def test_no_hay_eventos_antes_de_iniciar_la_partida(self):
        motor = MotorPartida(
            1,
            arena=arena_de_prueba(((100, 100),)),
            eventos=ProgramadorEventos(azar=random.Random(1)),
        )
        motor.agregar_jugador(1)
        avanzar(motor, ticks_para(60))
        assert motor.estado()["partida"] == {"estado": "esperando"}

    def test_el_primer_evento_sale_a_los_30_segundos(self):
        motor = motor_real()
        avanzar(motor, ticks_para(29.9))
        assert evento_actual(motor) is None
        avanzar(motor, 3)
        assert evento_actual(motor) is not None

    def test_dura_10_segundos_y_despues_desaparece(self):
        motor = motor_real()
        avanzar(motor, ticks_para(30))
        assert evento_actual(motor)["restante"] == 10
        avanzar(motor, ticks_para(5))
        assert evento_actual(motor)["restante"] == 5
        avanzar(motor, ticks_para(5) - 1)
        assert evento_actual(motor)["restante"] == 1  # le queda un último tick
        avanzar(motor, 1)
        assert evento_actual(motor) is None

    def test_el_evento_trae_clave_nombre_y_segundos(self):
        motor = motor_con_eventos("puntos_dobles")
        avanzar(motor, ticks_para(1))
        assert evento_actual(motor) == {
            "clave": "puntos_dobles",
            "nombre": "Puntos dobles",
            "restante": 3,
        }

    def test_la_cuenta_regresiva_baja_de_a_un_segundo(self):
        motor = motor_con_eventos("puntos_dobles", primer=1.0, duracion=10.0)
        avanzar(motor, ticks_para(1))
        vistos = []
        for _ in range(ticks_para(10) - 1):
            avanzar(motor, 1)
            restante = evento_actual(motor)["restante"]
            if not vistos or vistos[-1] != restante:
                vistos.append(restante)
        assert vistos == [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

    def test_el_siguiente_evento_llega_entre_30_y_45_segundos_despues(self):
        for semilla in range(6):
            motor = motor_real(semilla)
            observador = ObservadorConReloj(motor)
            motor.suscribir(observador)
            avanzar(motor, ticks_para(295))
            inicios = [t for _, t in observador.de_tipo(EVENTO_ESPECIAL_INICIADO)]
            fines = [t for _, t in observador.de_tipo(EVENTO_ESPECIAL_FINALIZADO)]
            assert inicios[0] == pytest.approx(30, abs=CICLO_S)
            for fin, siguiente in zip(fines, inicios[1:], strict=False):
                assert 30 - CICLO_S <= siguiente - fin <= 45 + CICLO_S
            for inicio, fin in zip(inicios, fines, strict=False):
                assert fin - inicio == pytest.approx(10, abs=CICLO_S)

    def test_nunca_se_repite_el_mismo_evento_seguido_y_solo_hay_uno_a_la_vez(self):
        motor = motor_real()
        programador = ProgramadorEventos(
            azar=random.Random(3),
            primer_evento_s=1,
            espera_minima_s=1,
            espera_maxima_s=1,
            duracion_s=1,
        )
        motor = MotorPartida(1, arena=arena_de_prueba(((100, 100),)), eventos=programador)
        motor.agregar_jugador(1)
        motor.iniciar_partida(300, 500)
        observador = ObservadorConReloj(motor)
        motor.suscribir(observador)
        avanzar(motor, ticks_para(60))
        claves = [d["evento"] for d, _ in observador.de_tipo(EVENTO_ESPECIAL_INICIADO)]
        assert len(claves) >= 15
        assert all(a != b for a, b in itertools.pairwise(claves))
        tipos = [t for t, _, _ in observador.eventos if t.startswith("evento_especial")]
        assert tipos[::2] == [EVENTO_ESPECIAL_INICIADO] * len(tipos[::2])
        assert tipos[1::2] == [EVENTO_ESPECIAL_FINALIZADO] * len(tipos[1::2])

    def test_se_avisa_a_los_clientes_cuando_empieza_y_cuando_termina(self):
        motor = motor_con_eventos("puntos_dobles")
        observador = ObservadorConReloj(motor)
        motor.suscribir(observador)
        avanzar(motor, ticks_para(5))  # empieza a 1 s, dura 3 s y el siguiente sale a los 6 s
        estados = [d for t, d, _ in observador.eventos if t == ESTADO_ACTUALIZADO]
        con_evento = [e for e in estados if "evento" in e["partida"]]
        assert con_evento, "tenía que avisar que empezó el evento"
        assert "evento" not in estados[-1]["partida"]  # y el aviso final ya no lo trae
        iniciado = observador.de_tipo(EVENTO_ESPECIAL_INICIADO)[0][0]
        assert iniciado["nombre"] == "Puntos dobles" and iniciado["duracion_s"] == 3.0
        assert observador.de_tipo(EVENTO_ESPECIAL_FINALIZADO)

    def test_el_registro_guarda_cuando_empieza_y_termina_un_evento(self):
        assert EVENTO_ESPECIAL_INICIADO in TIPOS_GUARDADOS
        assert EVENTO_ESPECIAL_FINALIZADO in TIPOS_GUARDADOS

    def test_el_gestor_crea_los_motores_con_eventos(self):
        async def crear():
            gestor = GestorMotores(ConnectionManager())
            con_escenario = gestor.obtener(1, "laboratorio")
            basico = gestor.obtener(2)
            await con_escenario.detener()
            await basico.detener()
            return con_escenario, basico

        con_escenario, basico = asyncio.run(crear())
        assert con_escenario._eventos_especiales is not None
        assert basico._eventos_especiales is not None

    def test_una_partida_nueva_vuelve_a_esperar_los_30_segundos(self):
        motor = motor_real()
        avanzar(motor, ticks_para(31))
        assert evento_actual(motor) is not None
        motor.terminar("administrador")
        assert evento_actual(motor) is None


class TestPuntosDobles:
    def test_durante_el_evento_lo_que_se_gana_vale_el_doble(self):
        motor = motor_con_eventos("puntos_dobles")
        avanzar(motor, ticks_para(1.5))
        motor.sumar_puntaje(1, 5)
        assert puntaje(motor) == 10

    def test_las_penalizaciones_no_se_duplican(self):
        motor = motor_con_eventos("puntos_dobles", primer=2.0)
        motor.sumar_puntaje(1, 20)  # antes del evento: vale lo normal
        avanzar(motor, ticks_para(2.5))
        assert evento_actual(motor) is not None
        motor.sumar_puntaje(1, -5)
        assert puntaje(motor) == 15

    def test_al_terminar_el_evento_los_puntos_vuelven_a_valer_lo_normal(self):
        motor = motor_con_eventos("puntos_dobles", primer=1.0, duracion=3.0)
        avanzar(motor, ticks_para(5))
        assert evento_actual(motor) is None
        motor.sumar_puntaje(1, 5)
        assert puntaje(motor) == 5

    def test_antes_del_evento_tampoco_se_duplica(self):
        motor = motor_con_eventos("puntos_dobles", primer=5.0)
        motor.sumar_puntaje(1, 5)
        assert puntaje(motor) == 5

    def test_una_celda_vale_el_doble_durante_el_evento(self):
        celda = Celda(1, 200, 100, 5)
        motor = motor_con_eventos("puntos_dobles", celdas=[celda], primer=1.0, duracion=5.0)
        avanzar(motor, ticks_para(1.2))  # ya empezó el evento
        motor.aplicar_entrada(1, "derecha", "presionado")
        avanzar(motor, ticks_para(1.5))  # camina de x = 100 a la celda en x = 200
        assert puntaje(motor) == 10

    def test_una_celda_recogida_sin_evento_vale_cinco(self):
        celda = Celda(1, 200, 100, 5)
        motor = motor_con_eventos("puntos_dobles", celdas=[celda], primer=50.0)
        motor.aplicar_entrada(1, "derecha", "presionado")
        avanzar(motor, ticks_para(1.5))
        assert puntaje(motor) == 5

    def test_extraer_del_reactor_vale_el_doble_pero_el_registro_cuenta_la_energia_normal(self):
        motor = motor_con_eventos("puntos_dobles", inicios=((REACTOR.x - 50, REACTOR.y),))
        observador = ObservadorConReloj(motor)
        motor.suscribir(observador)
        avanzar(motor, ticks_para(1.5))
        motor.aplicar_entrada(1, "accion", "presionado")
        avanzar(motor, 1)
        assert puntaje(motor) == 20
        accion = observador.de_tipo(ACCION_REALIZADA)[0][0]
        assert accion["puntos"] == 10  # la energía extraída: los logros y retos la cuentan normal

    def test_si_la_partida_termina_con_el_evento_activo_se_deshace(self):
        motor = motor_con_eventos("puntos_dobles", primer=1.0, duracion=100.0)
        observador = ObservadorConReloj(motor)
        motor.suscribir(observador)
        avanzar(motor, ticks_para(2))
        assert evento_actual(motor) is not None
        motor.terminar("administrador")
        assert evento_actual(motor) is None
        motor.sumar_puntaje(1, 5)
        assert puntaje(motor) == 5
        avanzar(motor, 1)
        assert observador.de_tipo(EVENTO_ESPECIAL_FINALIZADO)

    def test_si_el_evento_dura_mas_que_la_partida_no_vuelve_a_salir(self):
        motor = motor_con_eventos("puntos_dobles", primer=1.0, duracion=100.0)
        avanzar(motor, ticks_para(2))
        motor.terminar("tiempo")
        avanzar(motor, ticks_para(5))
        assert evento_actual(motor) is None

    def test_directo_pone_y_quita_el_multiplicador(self):
        motor = motor_con_eventos("puntos_dobles", primer=99.0)
        evento = PuntosDobles()
        evento.iniciar(motor)
        motor.sumar_puntaje(1, 3)
        evento.terminar(motor)
        motor.sumar_puntaje(1, 3)
        assert puntaje(motor) == 9  # 6 con el evento + 3 sin él


class TestInvasion:
    def distancias_al_reactor(self, motor):
        invasores = [g for g in guardianes_del_estado(motor) if g["id"] >= ID_PRIMER_INVASOR]
        return invasores, [math.hypot(g["x"] - REACTOR.x, g["y"] - REACTOR.y) for g in invasores]

    def test_al_empezar_aparecen_dos_guardianes_extra(self):
        motor = motor_con_eventos(
            "invasion", guardianes=[Guardian(1, 60, 60, Patrulla([(60, 60)]))]
        )
        assert [g["id"] for g in guardianes_del_estado(motor)] == [1]
        avanzar(motor, ticks_para(1.2))
        ids = [g["id"] for g in guardianes_del_estado(motor)]
        assert ids == [1, ID_PRIMER_INVASOR, ID_PRIMER_INVASOR + 1]
        assert INVASORES == 2

    def test_aparecen_cerca_del_reactor_y_en_lados_opuestos(self):
        for semilla in range(8):
            motor = motor_con_eventos("invasion", semilla=semilla)
            avanzar(motor, ticks_para(1.0))  # el tick en que aparecen
            invasores, distancias = self.distancias_al_reactor(motor)
            assert len(invasores) == 2
            assert all(d == pytest.approx(REACTOR.radio + 100, abs=5) for d in distancias)
            medio_x = (invasores[0]["x"] + invasores[1]["x"]) / 2
            medio_y = (invasores[0]["y"] + invasores[1]["y"]) / 2
            assert (medio_x, medio_y) == pytest.approx((REACTOR.x, REACTOR.y), abs=5)

    def test_al_terminar_el_evento_desaparecen_y_quedan_los_del_mapa(self):
        motor = motor_con_eventos(
            "invasion", guardianes=[Guardian(1, 60, 60, Patrulla([(60, 60)]))], duracion=3.0
        )
        avanzar(motor, ticks_para(2))
        assert len(guardianes_del_estado(motor)) == 3
        avanzar(motor, ticks_para(2.5))
        assert evento_actual(motor) is None
        assert [g["id"] for g in guardianes_del_estado(motor)] == [1]

    def test_si_la_partida_termina_en_plena_invasion_los_invasores_se_van(self):
        motor = motor_con_eventos("invasion", duracion=100.0)
        avanzar(motor, ticks_para(2))
        assert len(guardianes_del_estado(motor)) == 2
        motor.terminar("tiempo")
        assert guardianes_del_estado(motor) == []

    def test_cada_invasion_trae_invasores_nuevos_sin_acumularse(self):
        motor = motor_con_eventos("invasion", primer=1.0, duracion=2.0, espera=2.0)
        avanzar(motor, ticks_para(20))
        assert len(guardianes_del_estado(motor)) in (0, 2)

    def test_no_aparecen_sobre_paredes(self):
        paredes = [Obstaculo(600, 250, 40, 40, "barrera"), Obstaculo(320, 250, 40, 40, "barrera")]
        for semilla in range(10):
            motor = motor_con_eventos("invasion", obstaculos=paredes, semilla=semilla)
            avanzar(motor, ticks_para(1.0))  # el tick en que aparecen
            invasores, _ = self.distancias_al_reactor(motor)
            assert len(invasores) == 2
            for invasor in invasores:
                assert not any(toca(invasor["x"], invasor["y"], RADIO_GUARDIAN, p) for p in paredes)

    def test_no_aparecen_encima_de_un_jugador(self):
        for semilla in range(10):
            motor = motor_con_eventos("invasion", inicios=((620, 270),), semilla=semilla)
            avanzar(motor, ticks_para(1.0))  # el tick en que aparecen
            invasores, _ = self.distancias_al_reactor(motor)
            for invasor in invasores:
                distancia = math.hypot(invasor["x"] - 620, invasor["y"] - 270)
                assert distancia > RADIO_GUARDIAN + RADIO_JUGADOR

    def test_persiguen_aunque_el_jugador_este_lejos(self):
        motor = motor_con_eventos("invasion", inicios=((60, 60),), duracion=10.0)
        avanzar(motor, ticks_para(1.0))  # el tick en que aparecen
        jugador = (60, 60)

        def mas_cercano():
            invasores = [g for g in guardianes_del_estado(motor) if g["id"] >= ID_PRIMER_INVASOR]
            return min(math.hypot(g["x"] - jugador[0], g["y"] - jugador[1]) for g in invasores)

        antes = mas_cercano()
        assert antes > 150  # más lejos que el radio de detección de un guardián normal
        avanzar(motor, ticks_para(1))
        assert mas_cercano() < antes - 60

    def test_si_alcanzan_al_jugador_lo_penalizan(self):
        motor = motor_con_eventos("invasion", inicios=((60, 60),), duracion=10.0)
        observador = ObservadorConReloj(motor)
        motor.suscribir(observador)
        motor.sumar_puntaje(1, 20)
        avanzar(motor, ticks_para(9))
        penalizaciones = observador.de_tipo(JUGADOR_PENALIZADO)
        assert penalizaciones, "un invasor tenía que alcanzar al jugador"
        datos, _ = penalizaciones[0]
        assert datos["guardian_id"] >= ID_PRIMER_INVASOR and datos["puntos"] == -5
        assert puntaje(motor) == 15

    def test_la_invasion_directa_agrega_y_quita_sus_dos_guardianes(self):
        motor = motor_con_eventos("invasion", primer=99.0)
        evento = Invasion(random.Random(1))
        evento.iniciar(motor)
        assert len(guardianes_del_estado(motor)) == 2
        evento.terminar(motor)
        assert guardianes_del_estado(motor) == []