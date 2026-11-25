"""Partidas que quedan abiertas sin nadie: se cierran para que nadie quede trabado (RN-04)."""

import asyncio

from sqlalchemy.orm import sessionmaker

from app.models.partida import EstadoPartida, Partida
from app.realtime.connection_manager import ConnectionManager
from app.realtime.gestor_motores import GestorMotores
from app.repositories.partida_repository import PartidaRepository
from app.scripts import cerrar_partidas_activas


def fabrica_de(db_session):
    return sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)


def estado_de(db_session, partida_id):
    db_session.expire_all()
    return PartidaRepository(db_session).obtener_por_id(partida_id).estado


# repositorio


def test_cerrar_si_sigue_esperando_solo_cierra_las_que_no_iniciaron(db_session):
    repo = PartidaRepository(db_session)
    esperando = repo.crear(Partida())
    en_curso = repo.crear(Partida())
    repo.cambiar_estado(en_curso, EstadoPartida.en_curso)

    assert repo.cerrar_si_sigue_esperando(esperando.id) is True
    assert repo.cerrar_si_sigue_esperando(en_curso.id) is False
    assert repo.cerrar_si_sigue_esperando(9999) is False

    assert esperando.estado == EstadoPartida.finalizada and esperando.fecha_fin is not None
    assert estado_de(db_session, en_curso.id) == EstadoPartida.en_curso


def test_cerrar_activas_cierra_en_espera_y_en_curso_pero_no_toca_las_terminadas(db_session):
    repo = PartidaRepository(db_session)
    esperando = repo.crear(Partida())
    en_curso = repo.crear(Partida())
    repo.cambiar_estado(en_curso, EstadoPartida.en_curso)
    terminada = repo.crear(Partida())
    repo.cambiar_estado(terminada, EstadoPartida.finalizada)
    fin_original = terminada.fecha_fin

    assert repo.cerrar_activas() == 2

    for partida in (esperando, en_curso):
        assert estado_de(db_session, partida.id) == EstadoPartida.finalizada
    db_session.refresh(terminada)
    assert terminada.fecha_fin == fin_original


def test_el_script_de_arranque_cierra_las_activas(db_session, monkeypatch):
    PartidaRepository(db_session).crear(Partida())
    monkeypatch.setattr(cerrar_partidas_activas, "SessionLocal", fabrica_de(db_session))

    assert cerrar_partidas_activas.main() == 1


# gestor de motores: todos se van del lobby


def gestor_para(db_session, espera_s=0.05):
    canales = ConnectionManager()
    gestor = GestorMotores(canales, fabrica_de(db_session))
    gestor.espera_antes_de_cerrar_s = espera_s
    return gestor, canales


def test_si_todos_se_van_de_una_partida_sin_iniciar_se_cierra(db_session):
    partida = PartidaRepository(db_session).crear(Partida())
    gestor, _ = gestor_para(db_session)

    async def escenario():
        gestor.obtener(partida.id)  # alguien estaba en el lobby y se fue
        await gestor.liberar_si_esta_vacio(partida.id)
        await asyncio.sleep(0.2)

    asyncio.run(escenario())

    assert estado_de(db_session, partida.id) == EstadoPartida.finalizada


def test_si_alguien_vuelve_antes_de_la_espera_la_partida_sigue_abierta(db_session):
    partida = PartidaRepository(db_session).crear(Partida())
    gestor, _ = gestor_para(db_session, espera_s=0.1)

    async def escenario():
        gestor.obtener(partida.id)
        await gestor.liberar_si_esta_vacio(partida.id)
        motor = gestor.obtener(partida.id)  # recargó la página y volvió a entrar
        motor.agregar_jugador(1, "ana")
        await asyncio.sleep(0.3)
        await motor.detener()
        gestor.limpiar()

    asyncio.run(escenario())

    assert estado_de(db_session, partida.id) == EstadoPartida.esperando


def test_una_partida_en_curso_no_se_cierra_aunque_todos_se_vayan(db_session):
    """Esa sigue corriendo hasta el final para guardar su resultado (US-17)."""
    partida = PartidaRepository(db_session).crear(Partida())
    PartidaRepository(db_session).cambiar_estado(partida, EstadoPartida.en_curso)
    gestor, _ = gestor_para(db_session)

    async def escenario():
        motor = gestor.obtener(partida.id)
        motor.agregar_jugador(1, "ana")
        motor.agregar_jugador(2, "beto")
        motor.iniciar_partida(300, 500)
        motor.quitar_jugador(1)
        motor.quitar_jugador(2)
        await gestor.liberar_si_esta_vacio(partida.id)
        await asyncio.sleep(0.2)
        quedo = gestor.existente(partida.id) is motor
        await motor.detener()
        gestor.limpiar()
        return quedo

    assert asyncio.run(escenario()) is True
    assert estado_de(db_session, partida.id) == EstadoPartida.en_curso
