"""Sonidos de la partida (US-29): qué suena con cada cambio del estado; sin audio no se rompe."""

import os

import pygame
import pytest

from src import sonidos as modulo
from src.sonidos import CELDA, EVENTO, EXTRACCION, GOLPE, DetectorSonidos, Sonidos


def estado(puntaje=0, energia=100, celdas=(1, 2), estados=None, evento=None):
    estados = estados or {}
    partida = {"estado": "en_curso"}
    if evento:
        partida["evento"] = {"nombre": evento, "restante": 10}
    return {
        "jugadores": [
            {"jugador_id": 1, "puntaje": puntaje, "estado": estados.get(1, "normal")},
            {"jugador_id": 2, "puntaje": 0, "estado": estados.get(2, "normal")},
        ],
        "reactor": {"energia": energia, "capacidad": 100},
        "arena": {"celdas": [{"id": i, "x": 0, "y": 0} for i in celdas]},
        "partida": partida,
    }


def revisar(antes, despues, mi_id=1):
    detector = DetectorSonidos()
    detector.revisar(antes, mi_id)
    return detector.revisar(despues, mi_id)


def test_el_primer_estado_no_suena():
    assert DetectorSonidos().revisar(estado(puntaje=50), 1) == []


def test_extraer_del_reactor_suena():
    assert revisar(estado(), estado(puntaje=10, energia=90)) == [EXTRACCION]


def test_si_extrae_otro_no_me_suena_la_extraccion():
    assert revisar(estado(), estado(energia=90)) == []


def test_recoger_una_bolita_suena():
    assert revisar(estado(), estado(puntaje=5, celdas=(2,))) == [CELDA]


def test_que_el_reactor_se_recargue_no_suena():
    assert revisar(estado(energia=80), estado(energia=85)) == []


def test_un_golpe_de_guardian_suena_aunque_sea_a_otro_y_una_sola_vez():
    detector = DetectorSonidos()
    detector.revisar(estado(), 1)

    assert detector.revisar(estado(estados={2: "aturdido"}), 1) == [GOLPE]
    assert detector.revisar(estado(estados={2: "aturdido"}), 1) == []  # sigue aturdido


def test_el_inicio_de_un_evento_especial_suena_una_vez():
    detector = DetectorSonidos()
    detector.revisar(estado(), 1)

    assert detector.revisar(estado(evento="Puntos dobles"), 1) == [EVENTO]
    assert detector.revisar(estado(evento="Puntos dobles"), 1) == []
    assert detector.revisar(estado(evento="Invasión"), 1) == [EVENTO]


def test_reiniciar_olvida_el_estado_anterior():
    detector = DetectorSonidos()
    detector.revisar(estado(), 1)
    detector.reiniciar()

    assert detector.revisar(estado(puntaje=10, energia=90), 1) == []


# reproducción


@pytest.fixture
def audio_falso():
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.mixer.quit()
    try:
        pygame.mixer.init()
    except pygame.error:
        pytest.skip("no hay controlador de audio de prueba")
    yield
    pygame.mixer.quit()


def test_cada_efecto_se_genera_y_suena(audio_falso):
    reproductor = Sonidos()
    reproductor.precargar()
    assert len(reproductor._efectos) == 4

    for nombre in (EXTRACCION, CELDA, GOLPE, EVENTO):
        assert reproductor.reproducir(nombre) is True
        assert reproductor._efectos[nombre].get_length() > 0.1


def test_la_musica_es_el_tramo_de_40_segundos_y_se_repite(audio_falso):
    assert modulo.MUSICA_PARTIDA.exists()
    assert 39 < pygame.mixer.Sound(str(modulo.MUSICA_PARTIDA)).get_length() <= 40.1
    assert Sonidos().iniciar_musica() is True


def test_silenciar_apaga_musica_y_efectos(audio_falso):
    reproductor = Sonidos()
    reproductor.iniciar_musica()

    assert reproductor.alternar_silencio() is True
    assert reproductor.reproducir(GOLPE) is False
    assert reproductor.iniciar_musica() is False
    assert reproductor.alternar_silencio() is False


def test_sin_audio_no_se_rompe(monkeypatch):
    def falla():
        raise pygame.error("sin audio")

    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)
    monkeypatch.setattr(pygame.mixer, "init", falla)

    reproductor = Sonidos()
    assert reproductor.reproducir(GOLPE) is False
    assert reproductor.iniciar_musica() is False
    reproductor.detener_musica()
