"""Pruebas de la validación y los límites de las entradas del cliente (contrato de hardware)."""

import pytest

from app.realtime.entradas import (
    MAX_ENTRADAS_POR_SEGUNDO,
    Entrada,
    EntradaInvalida,
    FiltroEntradas,
    interpretar_entrada,
)


class Reloj:
    def __init__(self):
        self.ahora = 100.0

    def __call__(self):
        return self.ahora


def entrada(seq=None, control="arriba", estado="presionado"):
    return Entrada(control, estado, seq)


# interpretar_entrada 


def test_interpreta_una_entrada_valida():
    mensaje = {"tipo": "entrada", "control": "izquierda", "estado": "liberado", "seq": 4}

    assert interpretar_entrada(mensaje) == Entrada("izquierda", "liberado", 4)


def test_el_numero_de_secuencia_es_opcional():
    resultado = interpretar_entrada({"control": "accion", "estado": "presionado"})

    assert resultado.seq is None


def test_un_control_desconocido_da_el_detalle_del_contrato():
    with pytest.raises(EntradaInvalida, match="control desconocido: saltar"):
        interpretar_entrada({"control": "saltar", "estado": "presionado"})


def test_sin_control_tambien_es_invalida():
    with pytest.raises(EntradaInvalida, match="control desconocido: None"):
        interpretar_entrada({"estado": "presionado"})


def test_un_estado_desconocido_es_invalido():
    with pytest.raises(EntradaInvalida, match="estado desconocido: mantenido"):
        interpretar_entrada({"control": "arriba", "estado": "mantenido"})


@pytest.mark.parametrize("seq", ["7", 1.5, True, [1]])
def test_un_seq_que_no_es_entero_es_invalido(seq):
    with pytest.raises(EntradaInvalida, match="seq debe ser un entero"):
        interpretar_entrada({"control": "arriba", "estado": "presionado", "seq": seq})


#  FiltroEntradas: secuencia 


def test_admite_las_entradas_con_secuencia_creciente():
    filtro = FiltroEntradas(Reloj())

    assert [filtro.admite(entrada(seq)) for seq in (1, 2, 5)] == [True, True, True]


def test_descarta_las_repetidas_y_las_atrasadas():
    filtro = FiltroEntradas(Reloj())
    filtro.admite(entrada(5))

    assert not filtro.admite(entrada(5))  # repetida
    assert not filtro.admite(entrada(3))  # atrasada
    assert filtro.admite(entrada(6))


def test_sin_secuencia_siempre_admite():
    filtro = FiltroEntradas(Reloj())

    assert filtro.admite(entrada(None)) and filtro.admite(entrada(None))


# FiltroEntradas: 30 por segundo 


def test_descarta_lo_que_pasa_de_30_entradas_por_segundo():
    filtro = FiltroEntradas(Reloj())

    resultados = [filtro.admite(entrada(seq)) for seq in range(1, MAX_ENTRADAS_POR_SEGUNDO + 6)]

    assert resultados[:MAX_ENTRADAS_POR_SEGUNDO] == [True] * MAX_ENTRADAS_POR_SEGUNDO
    assert resultados[MAX_ENTRADAS_POR_SEGUNDO:] == [False] * 5


def test_pasado_un_segundo_vuelve_a_admitir():
    reloj = Reloj()
    filtro = FiltroEntradas(reloj)
    for seq in range(1, MAX_ENTRADAS_POR_SEGUNDO + 1):
        filtro.admite(entrada(seq))
    assert not filtro.admite(entrada(100))

    reloj.ahora += 1.0

    assert filtro.admite(entrada(101))


def test_una_entrada_descartada_por_el_limite_no_gasta_su_numero_de_secuencia():
    reloj = Reloj()
    filtro = FiltroEntradas(reloj)
    for seq in range(1, MAX_ENTRADAS_POR_SEGUNDO + 1):
        filtro.admite(entrada(seq))
    siguiente = MAX_ENTRADAS_POR_SEGUNDO + 1
    assert not filtro.admite(entrada(siguiente))  # descartada por el límite

    reloj.ahora += 1.0

    assert filtro.admite(entrada(siguiente))  # el cliente puede reenviarla