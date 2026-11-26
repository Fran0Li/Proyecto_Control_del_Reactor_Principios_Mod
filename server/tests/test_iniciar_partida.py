"""Iniciar la partida desde el lobby y verla terminar por el canal (US-17 y US-22)."""

import dataclasses
import threading
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import crear_token_acceso
from app.db.session import get_session
from app.main import app
from app.models.partida import EstadoPartida, Partida
from app.models.ranking import RankingGlobal
from app.models.usuario import Usuario
from app.realtime.connection_manager import manager
from app.realtime.gestor_motores import gestor_motores
from app.realtime.motor_partida import EN_CURSO
from app.repositories import PartidaRepository, UsuarioRepository


@pytest.fixture()
def client(db_session, monkeypatch):
    app.dependency_overrides[get_session] = lambda: db_session
    # los observadores del gestor escriben en la misma base de la prueba
    fabrica = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    monkeypatch.setattr(gestor_motores, "_fabrica_sesiones", fabrica)
    manager._canales.clear()
    gestor_motores.limpiar()
    try:
        with TestClient(app) as cliente:
            yield cliente
    finally:
        app.dependency_overrides.clear()
        manager._canales.clear()
        gestor_motores.limpiar()


def crear_usuario(db_session, nombre):
    return UsuarioRepository(db_session).crear(
        Usuario(nombre_usuario=nombre, correo=f"{nombre}@mail.com", contrasena_hash="hash")
    )


def cabecera(usuario):
    return {"Authorization": f"Bearer {crear_token_acceso(usuario.id, usuario.version_sesion)}"}


def partida_de(client, db_session, *nombres):
    usuarios = [crear_usuario(db_session, nombre) for nombre in nombres]
    partida = client.post("/partidas", headers=cabecera(usuarios[0])).json()["id"]
    for otro in usuarios[1:]:
        client.post(f"/partidas/{partida}/unirse", headers=cabecera(otro))
    return partida, usuarios


def iniciar(client, partida_id, usuario):
    return client.post(f"/partidas/{partida_id}/iniciar", headers=cabecera(usuario))


def recibir(canal, segundos=5.0):
    resultado = {}

    def leer():
        try:
            resultado["mensaje"] = canal.receive_json()
        except Exception as error:
            resultado["error"] = error

    hilo = threading.Thread(target=leer, daemon=True)
    hilo.start()
    hilo.join(segundos)
    if hilo.is_alive():
        pytest.fail(f"el servidor no envió nada en {segundos} s")
    if "error" in resultado:
        raise resultado["error"]
    return resultado["mensaje"]


def recibir_tipo(canal, tipo, maximo=200):
    for _ in range(maximo):
        mensaje = recibir(canal)
        if mensaje["tipo"] == tipo:
            return mensaje
    pytest.fail(f"no llegó {tipo}")


def esperar(condicion, segundos=5.0):
    """Los observadores guardan en otro hilo: se espera a que la base quede como se espera."""
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if condicion():
            return
        time.sleep(0.05)
    pytest.fail("la base no quedó como se esperaba")


def url_del_canal(partida_id, usuario):
    return f"/ws/partidas/{partida_id}?token={crear_token_acceso(usuario.id)}"


# el endpoint


def test_el_creador_inicia_la_partida(client, db_session):
    partida, (ana, _) = partida_de(client, db_session, "ana", "beto")

    respuesta = iniciar(client, partida, ana)

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "en_curso"
    db_session.expire_all()
    assert db_session.get(Partida, partida).fecha_inicio is not None
    assert gestor_motores.existente(partida).estado_partida == EN_CURSO


def test_solo_el_creador_puede_iniciarla(client, db_session):
    partida, (_, beto) = partida_de(client, db_session, "ana", "beto")

    respuesta = iniciar(client, partida, beto)

    assert respuesta.status_code == 403


def test_sin_sesion_no_se_puede_iniciar(client, db_session):
    partida, _ = partida_de(client, db_session, "ana", "beto")

    assert client.post(f"/partidas/{partida}/iniciar").status_code == 401


def test_hacen_falta_al_menos_dos_jugadores(client, db_session):
    partida, (ana,) = partida_de(client, db_session, "ana")

    respuesta = iniciar(client, partida, ana)

    assert respuesta.status_code == 409
    assert "al menos 2" in respuesta.json()["detail"]


def test_el_minimo_de_jugadores_se_puede_cambiar(client, db_session, monkeypatch):
    otra_config = dataclasses.replace(settings, partida_minimo_jugadores=1)
    monkeypatch.setattr("app.services.partida_service.settings", otra_config)
    partida, (ana,) = partida_de(client, db_session, "ana")

    assert iniciar(client, partida, ana).status_code == 200


def test_no_se_inicia_dos_veces(client, db_session):
    partida, (ana, _) = partida_de(client, db_session, "ana", "beto")
    iniciar(client, partida, ana)

    assert iniciar(client, partida, ana).status_code == 409


def test_una_partida_que_no_existe(client, db_session):
    ana = crear_usuario(db_session, "ana")

    assert iniciar(client, 999, ana).status_code == 404


def test_iniciada_ya_no_aparece_ni_acepta_jugadores(client, db_session):
    partida, (ana, _) = partida_de(client, db_session, "ana", "beto")
    caro = crear_usuario(db_session, "caro")
    iniciar(client, partida, ana)

    assert client.get("/partidas").json() == []
    unirse = client.post(f"/partidas/{partida}/unirse", headers=cabecera(caro))
    assert unirse.status_code == 409


# la partida completa por el canal


def test_partida_completa_del_inicio_al_ranking(client, db_session):
    partida, (ana, beto) = partida_de(client, db_session, "ana", "beto")
    # una partida de 1 segundo para no esperar 5 minutos
    db_session.get(Partida, partida).tiempo_limite_segundos = 1
    db_session.commit()

    with client.websocket_connect(url_del_canal(partida, ana)) as canal_ana:
        with client.websocket_connect(url_del_canal(partida, beto)) as canal_beto:
            assert iniciar(client, partida, ana).status_code == 200

            inicio = recibir_tipo(canal_beto, "partida_iniciada")
            assert inicio["tiempo_limite"] == 1
            assert inicio["jugadores"] == [ana.id, beto.id]

            gestor_motores.existente(partida).sumar_puntaje(beto.id, 25)
            fin = recibir_tipo(canal_ana, "partida_finalizada")

    assert fin["ganador_id"] == beto.id
    assert fin["motivo"] == "tiempo"
    assert [(p["nombre"], p["posicion"]) for p in fin["posiciones"]] == [("beto", 1), ("ana", 2)]

    def guardado():
        db_session.expire_all()
        ranking = db_session.get(RankingGlobal, beto.id)
        terminada = db_session.get(Partida, partida).estado == EstadoPartida.finalizada
        return terminada and ranking is not None

    esperar(guardado)
    puestos = {
        p.jugador_id: p.posicion_final
        for p in PartidaRepository(db_session).listar_participaciones(partida)
    }
    assert puestos == {beto.id: 1, ana.id: 2}
    assert db_session.get(RankingGlobal, beto.id).victorias == 1


def test_el_estado_trae_el_nombre_de_cada_jugador(client, db_session):
    partida, (ana, _) = partida_de(client, db_session, "ana", "beto")

    with client.websocket_connect(url_del_canal(partida, ana)) as canal:
        estado = recibir_tipo(canal, "estado")

    assert estado["jugadores"][0]["nombre"] == "ana"
    assert estado["partida"]["estado"] == "esperando"
