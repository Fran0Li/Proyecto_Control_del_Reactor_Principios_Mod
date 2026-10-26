"""Movimiento por el canal WebSocket: entradas, estado para todos y latencia (US-25)."""

import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.core.security import crear_token_acceso
from app.db.session import get_session
from app.main import app
from app.models.usuario import Usuario
from app.realtime.connection_manager import manager
from app.realtime.gestor_motores import gestor_motores
from app.realtime.motor_partida import ANCHO_ARENA, PUNTOS_DE_INICIO
from app.repositories import UsuarioRepository


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    try:
        with TestClient(app) as cliente:  # un solo ciclo de eventos para todas las conexiones
            yield cliente
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def tiempo_real_limpio():
    """Los canales y los motores viven en la memoria del servidor: cada prueba empieza limpia."""
    manager._canales.clear()
    gestor_motores.limpiar()
    yield
    manager._canales.clear()
    gestor_motores.limpiar()


def crear_jugadores(db_session, cantidad):
    repo = UsuarioRepository(db_session)
    return [
        repo.crear(
            Usuario(nombre_usuario=f"jugador{i}", correo=f"j{i}@mail.com", contrasena_hash="hash")
        ).id
        for i in range(1, cantidad + 1)
    ]


def partida_de_dos(client, db_session):
    ana, beto = crear_jugadores(db_session, 2)
    partida = client.post("/partidas", json={"creador_id": ana}).json()["id"]
    assert client.post(f"/partidas/{partida}/unirse", json={"jugador_id": beto}).status_code == 200
    return partida, ana, beto


def url_del_canal(partida_id, jugador_id):
    return f"/ws/partidas/{partida_id}?token={crear_token_acceso(jugador_id)}"


def recibir(canal, segundos=3.0):
    """Lee un mensaje; si el servidor no manda nada a tiempo, la prueba falla (no se cuelga)."""
    resultado = {}

    def leer():
        try:
            resultado["mensaje"] = canal.receive_json()
        except Exception as error:  # la conexión se cerró
            resultado["error"] = error

    hilo = threading.Thread(target=leer, daemon=True)
    hilo.start()
    hilo.join(segundos)
    if hilo.is_alive():
        pytest.fail(f"el servidor no envió nada en {segundos} s")
    if "error" in resultado:
        raise resultado["error"]
    return resultado["mensaje"]


def recibir_hasta(canal, condicion, maximo=60):
    """Lee mensajes hasta que uno cumpla la condición (se ignoran los demás avisos)."""
    for _ in range(maximo):
        mensaje = recibir(canal)
        if condicion(mensaje):
            return mensaje
    pytest.fail("no llegó el mensaje esperado")


def es_estado(mensaje):
    return mensaje["tipo"] == "estado"


def x_de(mensaje, jugador_id):
    return next(j["x"] for j in mensaje["jugadores"] if j["jugador_id"] == jugador_id)


def con_dos_jugadores(mensaje):
    return es_estado(mensaje) and len(mensaje["jugadores"]) == 2


def entrada(control, estado, seq):
    return {
        "tipo": "entrada",
        "control": control,
        "estado": estado,
        "origen": "teclado",
        "seq": seq,
    }


#  posición inicial y movimiento


def test_el_jugador_recibe_su_posicion_inicial_al_entrar(client, db_session):
    partida, ana, _ = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as canal:
        estado = recibir_hasta(canal, es_estado)

    x, y = PUNTOS_DE_INICIO[0]
    assert estado["jugadores"] == [{"jugador_id": ana, "x": x, "y": y}]
    assert estado["arena"]["ancho"] == ANCHO_ARENA


def test_presionar_una_direccion_mueve_al_jugador_y_avisa(client, db_session):
    partida, ana, _ = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as canal:
        inicial = x_de(recibir_hasta(canal, es_estado), ana)
        canal.send_json(entrada("derecha", "presionado", 1))
        movido = recibir_hasta(canal, lambda m: es_estado(m) and x_de(m, ana) > inicial)

    assert x_de(movido, ana) > inicial


def test_soltar_el_control_detiene_al_jugador(client, db_session):
    partida, ana, _ = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as canal:
        inicial = x_de(recibir_hasta(canal, es_estado), ana)
        canal.send_json(entrada("derecha", "presionado", 1))
        recibir_hasta(canal, lambda m: es_estado(m) and x_de(m, ana) > inicial)
        canal.send_json(entrada("derecha", "liberado", 2))
        time.sleep(0.3)  # varios ciclos del motor
        motor = gestor_motores.existente(partida)
        assert motor.controles_presionados(ana) == frozenset()
        quieto = motor.estado()
        time.sleep(0.2)
        assert motor.estado() == quieto


def test_todos_los_jugadores_ven_el_movimiento_de_los_demas(client, db_session):
    partida, ana, beto = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as canal_ana:
        with client.websocket_connect(url_del_canal(partida, beto)) as canal_beto:
            inicial = x_de(recibir_hasta(canal_beto, con_dos_jugadores), beto)
            canal_beto.send_json(entrada("derecha", "presionado", 1))
            visto_por_ana = recibir_hasta(
                canal_ana, lambda m: con_dos_jugadores(m) and x_de(m, beto) > inicial
            )

    assert x_de(visto_por_ana, beto) > inicial


def test_la_posicion_llega_a_los_clientes_en_menos_de_500_ms(client, db_session):
    """RNF-02: desde que el cliente manda la tecla hasta que recibe la nueva posición."""
    partida, ana, _ = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as canal:
        inicial = x_de(recibir_hasta(canal, es_estado), ana)
        enviado = time.monotonic()
        canal.send_json(entrada("derecha", "presionado", 1))
        recibir_hasta(canal, lambda m: es_estado(m) and x_de(m, ana) > inicial)
        tardo = time.monotonic() - enviado

    assert tardo < 0.5


def test_quien_se_va_desaparece_del_estado_de_los_demas(client, db_session):
    partida, ana, beto = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as canal_ana:
        with client.websocket_connect(url_del_canal(partida, beto)):
            recibir_hasta(canal_ana, con_dos_jugadores)
        quedan = recibir_hasta(canal_ana, lambda m: es_estado(m) and len(m["jugadores"]) == 1)

    assert [j["jugador_id"] for j in quedan["jugadores"]] == [ana]


# entradas inválidas y descartadas


def test_una_entrada_invalida_recibe_el_error_del_contrato(client, db_session):
    partida, ana, _ = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as canal:
        canal.send_json({"tipo": "entrada", "control": "saltar", "estado": "presionado", "seq": 1})
        error = recibir_hasta(canal, lambda m: m["tipo"] == "error")

    assert error == {
        "tipo": "error",
        "codigo": "entrada_invalida",
        "detalle": "control desconocido: saltar",
    }


def test_un_mensaje_que_no_es_json_recibe_error(client, db_session):
    partida, ana, _ = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as canal:
        canal.send_text("esto no es json")
        error = recibir_hasta(canal, lambda m: m["tipo"] == "error")

    assert error["codigo"] == "json_invalido"


def test_los_mensajes_de_otro_tipo_se_ignoran_sin_romper_el_canal(client, db_session):
    partida, ana, _ = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as canal:
        inicial = x_de(recibir_hasta(canal, es_estado), ana)
        canal.send_json({"tipo": "dispositivo", "estado": "conectado", "id": "CR-PAD-01"})
        canal.send_json(entrada("derecha", "presionado", 1))
        movido = recibir_hasta(canal, lambda m: es_estado(m) and x_de(m, ana) > inicial)

    assert x_de(movido, ana) > inicial


def test_una_entrada_atrasada_se_descarta_y_el_jugador_sigue_moviendose(client, db_session):
    partida, ana, _ = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as canal:
        inicial = x_de(recibir_hasta(canal, es_estado), ana)
        canal.send_json(entrada("derecha", "presionado", 5))
        antes = x_de(recibir_hasta(canal, lambda m: es_estado(m) and x_de(m, ana) > inicial), ana)
        canal.send_json(entrada("derecha", "liberado", 3))  # atrasada: no debe detenerlo
        despues = recibir_hasta(canal, lambda m: es_estado(m) and x_de(m, ana) > antes)

    assert x_de(despues, ana) > antes


# conexiones


def test_al_reconectar_el_servidor_suelta_los_controles_del_jugador(client, db_session):
    partida, ana, _ = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as vieja:
        inicial = x_de(recibir_hasta(vieja, es_estado), ana)
        vieja.send_json(entrada("derecha", "presionado", 1))
        recibir_hasta(vieja, lambda m: es_estado(m) and x_de(m, ana) > inicial)
        with client.websocket_connect(url_del_canal(partida, ana)) as nueva:
            recibir_hasta(nueva, es_estado)
            motor = gestor_motores.existente(partida)
            assert motor.controles_presionados(ana) == frozenset()


def test_el_motor_se_detiene_cuando_se_van_todos_los_jugadores(client, db_session):
    partida, ana, beto = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as canal_ana:
        recibir_hasta(canal_ana, es_estado)
        with client.websocket_connect(url_del_canal(partida, beto)):
            assert gestor_motores.existente(partida) is not None
        assert gestor_motores.existente(partida) is not None  # ana sigue dentro

    assert gestor_motores.existente(partida) is None