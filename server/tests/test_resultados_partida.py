"""Lo que se guarda al terminar la partida (US-17): resultado, eventos y ranking global."""

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models.evento import Evento
from app.models.partida import EstadoPartida, Partida
from app.models.ranking import RankingGlobal
from app.models.usuario import Usuario
from app.realtime.actualizador_ranking import ActualizadorRanking
from app.realtime.cierre_partida import CierrePartida
from app.realtime.eventos import (
    ACCION_REALIZADA,
    ESTADO_ACTUALIZADO,
    PARTIDA_FINALIZADA,
    PARTIDA_INICIADA,
    EventoPartida,
)
from app.realtime.registro_eventos import RegistroEventos
from app.repositories import PartidaRepository, UsuarioRepository


@pytest.fixture()
def fabrica(db_session):
    return sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)


def crear_usuario(db_session, nombre):
    return UsuarioRepository(db_session).crear(
        Usuario(nombre_usuario=nombre, correo=f"{nombre}@mail.com", contrasena_hash="hash")
    )


def partida_con(db_session, *jugadores):
    repo = PartidaRepository(db_session)
    partida = repo.crear(Partida(estado=EstadoPartida.en_curso))
    for jugador in jugadores:
        repo.agregar_participante(partida.id, jugador.id)
    return partida


def fin(partida_id, ana, beto, puntaje_ana=300, puntaje_beto=120, ganador="ana"):
    ganador_id = {"ana": ana.id, "beto": beto.id, None: None}[ganador]
    posiciones = sorted(
        [(ana.id, "ana", puntaje_ana), (beto.id, "beto", puntaje_beto)], key=lambda j: -j[2]
    )
    return EventoPartida(
        PARTIDA_FINALIZADA,
        partida_id,
        {
            "puntajes": {ana.id: puntaje_ana, beto.id: puntaje_beto},
            "ganador_id": ganador_id,
            "posiciones": [
                {"jugador_id": i, "nombre": n, "puntaje": p, "posicion": puesto}
                for puesto, (i, n, p) in enumerate(posiciones, start=1)
            ],
            "motivo": "tiempo",
            "duracion_s": 300,
        },
    )


def enviar(observador, *eventos):
    async def correr():
        for evento in eventos:
            await observador.al_evento(evento)

    asyncio.run(correr())


# cierre de la partida


def test_al_terminar_la_partida_queda_finalizada_con_puntajes_y_puestos(db_session, fabrica):
    ana, beto = crear_usuario(db_session, "ana"), crear_usuario(db_session, "beto")
    partida = partida_con(db_session, ana, beto)

    enviar(CierrePartida(fabrica), fin(partida.id, ana, beto))

    db_session.expire_all()
    assert db_session.get(Partida, partida.id).estado == EstadoPartida.finalizada
    assert db_session.get(Partida, partida.id).fecha_fin is not None
    resultado = {
        p.jugador_id: (p.puntaje_final, p.posicion_final)
        for p in PartidaRepository(db_session).listar_participaciones(partida.id)
    }
    assert resultado == {ana.id: (300, 1), beto.id: (120, 2)}


def test_al_terminar_un_jugador_puede_crear_otra_partida(db_session, fabrica):
    ana, beto = crear_usuario(db_session, "ana"), crear_usuario(db_session, "beto")
    partida = partida_con(db_session, ana, beto)
    assert PartidaRepository(db_session).jugador_en_partida_activa(ana.id)  # RN-04

    enviar(CierrePartida(fabrica), fin(partida.id, ana, beto))

    db_session.expire_all()
    assert not PartidaRepository(db_session).jugador_en_partida_activa(ana.id)


# ranking global


def test_el_ranking_suma_puntos_y_la_victoria_al_ganador(db_session, fabrica):
    ana, beto = crear_usuario(db_session, "ana"), crear_usuario(db_session, "beto")
    partida = partida_con(db_session, ana, beto)

    enviar(ActualizadorRanking(fabrica), fin(partida.id, ana, beto))

    db_session.expire_all()
    assert (
        db_session.get(RankingGlobal, ana.id).puntos_totales,
        db_session.get(RankingGlobal, ana.id).victorias,
    ) == (300, 1)
    assert (
        db_session.get(RankingGlobal, beto.id).puntos_totales,
        db_session.get(RankingGlobal, beto.id).victorias,
    ) == (120, 0)


def test_el_ranking_acumula_partida_tras_partida(db_session, fabrica):
    ana, beto = crear_usuario(db_session, "ana"), crear_usuario(db_session, "beto")
    primera, segunda = partida_con(db_session, ana, beto), partida_con(db_session, ana, beto)
    actualizador = ActualizadorRanking(fabrica)

    enviar(actualizador, fin(primera.id, ana, beto), fin(segunda.id, ana, beto, 50, 400, "beto"))

    db_session.expire_all()
    fila = db_session.get(RankingGlobal, beto.id)
    assert (fila.puntos_totales, fila.victorias) == (520, 1)


def test_con_empate_nadie_suma_victoria(db_session, fabrica):
    ana, beto = crear_usuario(db_session, "ana"), crear_usuario(db_session, "beto")
    partida = partida_con(db_session, ana, beto)

    enviar(ActualizadorRanking(fabrica), fin(partida.id, ana, beto, 200, 200, None))

    db_session.expire_all()
    assert db_session.get(RankingGlobal, ana.id).victorias == 0
    assert db_session.get(RankingGlobal, beto.id).victorias == 0


def test_el_ranking_ignora_los_demas_eventos(db_session, fabrica):
    ana = crear_usuario(db_session, "ana")
    partida = partida_con(db_session, ana)

    enviar(ActualizadorRanking(fabrica), EventoPartida(ESTADO_ACTUALIZADO, partida.id, {}))

    assert db_session.get(RankingGlobal, ana.id) is None


# tabla eventos


def eventos(db_session, partida_id):
    db_session.expire_all()
    consulta = select(Evento).where(Evento.partida_id == partida_id).order_by(Evento.id)
    return list(db_session.scalars(consulta))


def test_guarda_inicio_acciones_y_fin_pero_no_cada_estado(db_session, fabrica):
    ana, beto = crear_usuario(db_session, "ana"), crear_usuario(db_session, "beto")
    partida = partida_con(db_session, ana, beto)
    accion = {"jugador_id": ana.id, "accion": "reactor", "puntos": 10}

    enviar(
        RegistroEventos(fabrica),
        EventoPartida(PARTIDA_INICIADA, partida.id, {"tiempo_limite": 300}),
        EventoPartida(ESTADO_ACTUALIZADO, partida.id, {"jugadores": []}),
        EventoPartida(ACCION_REALIZADA, partida.id, accion),
        fin(partida.id, ana, beto),
    )

    guardados = eventos(db_session, partida.id)
    assert [e.tipo for e in guardados] == [PARTIDA_INICIADA, ACCION_REALIZADA, PARTIDA_FINALIZADA]
    assert guardados[1].jugador_id == ana.id
    assert guardados[1].datos == accion
    assert guardados[2].datos["ganador_id"] == ana.id
    assert guardados[2].datos["puntajes"] == {str(ana.id): 300, str(beto.id): 120}
