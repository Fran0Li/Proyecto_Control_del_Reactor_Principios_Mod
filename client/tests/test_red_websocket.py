"""Prueba la conexión WebSocket de escritorio contra un servidor local de verdad.

La del navegador usa `window` de pygbag, que no existe en la PC: se prueba con una ventana falsa
que anota el JavaScript que recibiría.
"""

import asyncio
import json
import platform

import pytest
import websockets

from src.red.websocket import ConexionEscritorio, ConexionNavegador


async def con_servidor(manejador, escenario):
    async with websockets.serve(manejador, "127.0.0.1", 0) as servidor:
        puerto = servidor.sockets[0].getsockname()[1]
        return await escenario(f"ws://127.0.0.1:{puerto}/ws/prueba")


async def esperar(condicion, segundos=3.0):
    limite = asyncio.get_running_loop().time() + segundos
    while asyncio.get_running_loop().time() < limite:
        if condicion():
            return True
        await asyncio.sleep(0.01)
    return False


def test_recibe_los_mensajes_del_servidor():
    async def manejador(ws):
        await ws.send(json.dumps({"tipo": "jugador_conectado", "conectados": [1]}))
        await ws.wait_closed()

    async def escenario(url):
        conexion = ConexionEscritorio(url)
        await conexion.conectar()
        assert conexion.estado == "conectando"
        recibidos = []
        assert await esperar(lambda: recibidos.extend(conexion.recibir()) or recibidos)
        assert conexion.estado == "abierta"
        conexion.cerrar()
        return recibidos

    recibidos = asyncio.run(con_servidor(manejador, escenario))
    assert recibidos == [{"tipo": "jugador_conectado", "conectados": [1]}]


def test_envia_al_servidor_y_recibe_la_respuesta():
    async def manejador(ws):
        async for texto in ws:
            await ws.send(texto)  # eco

    async def escenario(url):
        conexion = ConexionEscritorio(url)
        await conexion.conectar()
        assert await esperar(lambda: conexion.estado == "abierta")
        conexion.enviar({"tipo": "entrada", "control": "arriba"})
        recibidos = []
        assert await esperar(lambda: recibidos.extend(conexion.recibir()) or recibidos)
        conexion.cerrar()
        return recibidos

    recibidos = asyncio.run(con_servidor(manejador, escenario))
    assert recibidos == [{"tipo": "entrada", "control": "arriba"}]


def test_un_mensaje_que_no_es_json_se_ignora_y_la_conexion_sigue():
    async def manejador(ws):
        await ws.send("esto no es json")
        await ws.send(json.dumps({"tipo": "valido"}))
        await ws.wait_closed()

    async def escenario(url):
        conexion = ConexionEscritorio(url)
        await conexion.conectar()
        recibidos = []
        assert await esperar(lambda: recibidos.extend(conexion.recibir()) or recibidos)
        estado = conexion.estado
        conexion.cerrar()
        return recibidos, estado

    recibidos, estado = asyncio.run(con_servidor(manejador, escenario))
    assert recibidos == [{"tipo": "valido"}]
    assert estado == "abierta"


def test_cerrar_cierra_la_conexion_del_lado_del_servidor():
    async def escenario(url):
        servidor_vio_el_cierre = asyncio.Event()

        async def manejador(ws):
            try:
                await ws.wait_closed()
            finally:
                servidor_vio_el_cierre.set()

        async with websockets.serve(manejador, "127.0.0.1", 0) as servidor:
            puerto = servidor.sockets[0].getsockname()[1]
            conexion = ConexionEscritorio(f"ws://127.0.0.1:{puerto}/x")
            await conexion.conectar()
            assert await esperar(lambda: conexion.estado == "abierta")
            conexion.cerrar()
            assert conexion.estado == "cerrada"
            await asyncio.wait_for(servidor_vio_el_cierre.wait(), timeout=3)

    asyncio.run(escenario(None))


def test_servidor_caido_deja_el_estado_en_error():
    async def escenario():
        conexion = ConexionEscritorio("ws://127.0.0.1:9/ws/prueba")
        await conexion.conectar()
        assert await esperar(lambda: conexion.estado.startswith("error"))
        assert conexion.recibir() == []

    asyncio.run(escenario())


def test_no_congela_el_ciclo_mientras_espera():
    async def manejador(ws):
        await asyncio.sleep(0.2)
        await ws.send(json.dumps({"tipo": "tarde"}))
        await ws.wait_closed()

    async def escenario(url):
        frames = 0
        conexion = ConexionEscritorio(url)
        await conexion.conectar()
        while not conexion.recibir():
            frames += 1  # cada vuelta es un "frame" del juego
            await asyncio.sleep(0)
            if frames > 1_000_000:
                break
        conexion.cerrar()
        return frames

    assert asyncio.run(con_servidor(manejador, escenario)) > 1


# navegador (con una ventana falsa)


class VentanaFalsa:
    def __init__(self):
        self.codigos = []
        self.respuestas = {}

    def eval(self, js):
        self.codigos.append(js)
        for clave, valor in self.respuestas.items():
            if clave in js:
                return valor
        return ""


@pytest.fixture()
def ventana(monkeypatch):
    falsa = VentanaFalsa()
    monkeypatch.setattr(platform, "window", falsa, raising=False)
    return falsa


def test_navegador_abre_el_websocket_nativo(ventana):
    conexion = ConexionNavegador("ws://192.168.1.5:8000/ws/partidas/3?jugador_id=2")
    asyncio.run(conexion.conectar())
    js = ventana.codigos[-1]
    assert 'new WebSocket("ws://192.168.1.5:8000/ws/partidas/3?jugador_id=2")' in js
    assert "window.__cr.ws.close()" in js  # si había una conexión anterior, se cierra


def test_navegador_lee_el_estado_y_los_mensajes(ventana):
    evento = {"tipo": "jugador_conectado", "conectados": [1, 2]}
    ventana.respuestas = {
        "__cr.estado : 'desconectada'": "abierta",
        "cola.splice": json.dumps([json.dumps(evento)]),
    }
    conexion = ConexionNavegador("ws://x/y")
    assert conexion.estado == "abierta"
    assert conexion.recibir() == [evento]


def test_navegador_envia_el_mensaje_como_literal_de_javascript(ventana):
    conexion = ConexionNavegador("ws://x/y")
    mensaje = {"tipo": "entrada", "control": "arriba", "nota": 'con "comillas"'}
    conexion.enviar(mensaje)
    assert json.dumps(json.dumps(mensaje)) in ventana.codigos[-1]


def test_navegador_cerrar_cierra_el_websocket(ventana):
    ConexionNavegador("ws://x/y").cerrar()
    assert ".close()" in ventana.codigos[-1]