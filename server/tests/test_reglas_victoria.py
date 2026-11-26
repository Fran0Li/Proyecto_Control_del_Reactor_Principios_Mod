from app.realtime.reglas_victoria import (
    POR_PUNTAJE,
    POR_TIEMPO,
    ReglasVictoria,
    ganador,
    ordenar,
)

reglas = ReglasVictoria(tiempo_limite_s=300, puntaje_objetivo=500)


def test_sigue_mientras_haya_tiempo_y_nadie_llegue_al_objetivo():
    assert reglas.motivo_de_fin(120, [100, 499]) is None


def test_termina_al_llegar_a_la_puntuacion_objetivo():
    assert reglas.motivo_de_fin(120, [100, 500]) == POR_PUNTAJE


def test_termina_cuando_se_acaba_el_tiempo():
    assert reglas.motivo_de_fin(300, [100, 200]) == POR_TIEMPO


def test_si_pasan_las_dos_cosas_a_la_vez_cuenta_el_puntaje():
    assert reglas.motivo_de_fin(300, [520]) == POR_PUNTAJE


def test_el_tiempo_restante_no_baja_de_cero():
    assert reglas.tiempo_restante(250) == 50
    assert reglas.tiempo_restante(400) == 0


def test_ordena_de_mayor_a_menor_puntaje():
    posiciones = ordenar([(1, "ana", 120), (2, "beto", 300), (3, "caro", 80)])

    assert [(p.nombre, p.posicion) for p in posiciones] == [("beto", 1), ("ana", 2), ("caro", 3)]
    assert ganador(posiciones) == 2


def test_los_empatados_comparten_el_puesto():
    posiciones = ordenar([(1, "ana", 200), (2, "beto", 300), (3, "caro", 200), (4, "dani", 50)])

    assert [p.posicion for p in posiciones] == [1, 2, 2, 4]


def test_con_empate_en_el_primer_lugar_no_hay_ganador():
    posiciones = ordenar([(1, "ana", 300), (2, "beto", 300)])

    assert [p.posicion for p in posiciones] == [1, 1]
    assert ganador(posiciones) is None


def test_sin_jugadores_no_hay_ganador():
    assert ganador(ordenar([])) is None
