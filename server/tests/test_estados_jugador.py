"""Pruebas de los estados del jugador (US-15, patrón State): sin motor ni red."""

from app.realtime.estados_jugador import (
    ATURDIDO,
    DURACION_ATURDIDO_S,
    DURACION_ESCUDO_S,
    ESCUDADO,
    NORMAL,
    Aturdido,
    Escudado,
    Normal,
)


def test_normal_se_mueve_y_es_vulnerable():
    estado = Normal()
    assert estado.nombre == NORMAL
    assert estado.puede_moverse
    assert estado.vulnerable


def test_un_golpe_aturde_al_jugador_normal():
    assert isinstance(Normal().golpeado(), Aturdido)


def test_normal_no_cambia_con_el_tiempo():
    estado = Normal()
    assert estado.actualizar(100.0) is estado


def test_aturdido_no_se_mueve_y_no_se_golpea_otra_vez():
    estado = Aturdido()
    assert estado.nombre == ATURDIDO
    assert not estado.puede_moverse
    assert not estado.vulnerable
    assert estado.golpeado() is estado


def test_aturdido_sigue_igual_antes_de_terminar_su_tiempo():
    estado = Aturdido()
    assert estado.actualizar(DURACION_ATURDIDO_S - 0.1) is estado


def test_aturdido_pasa_a_escudado_al_terminar_su_tiempo():
    estado = Aturdido()
    estado.actualizar(DURACION_ATURDIDO_S - 1.0)
    assert isinstance(estado.actualizar(1.0), Escudado)


def test_escudado_se_mueve_pero_no_es_vulnerable():
    estado = Escudado()
    assert estado.nombre == ESCUDADO
    assert estado.puede_moverse
    assert not estado.vulnerable
    assert estado.golpeado() is estado


def test_escudado_vuelve_a_normal_al_terminar_su_tiempo():
    estado = Escudado()
    assert estado.actualizar(DURACION_ESCUDO_S - 0.5) is estado
    assert isinstance(estado.actualizar(0.5), Normal)


def test_la_duracion_se_puede_cambiar():
    assert isinstance(Aturdido(duracion_s=0.5).actualizar(0.5), Escudado)
    assert isinstance(Escudado(duracion_s=0.5).actualizar(0.5), Normal)