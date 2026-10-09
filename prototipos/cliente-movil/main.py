"""Prototipo: el mismo cliente pygame en PC y en el navegador del celular (pygbag).

Escritorio:  python main.py              (SERVIDOR=host:puerto para otro servidor)
Navegador:   pygbag --bind <IP-de-la-PC> --port 8001 .   y abrir http://<IP-de-la-PC>:8001

Prueba lo que hay que validar antes de seguir con el cliente real:
- ciclo principal async (obligatorio en pygbag),
- WebSocket desde el navegador hacia el backend,
- botones táctiles y teclado con la misma interfaz y el mismo mensaje del contrato,
- latencia ida y vuelta (RNF-02: menos de 500 ms).
"""

import asyncio
import time

import pygame

from entrada import Tactil, Teclado
from red import EN_NAVEGADOR, crear_conexion, url_del_servidor

ANCHO, ALTO = 960, 540
FONDO = (12, 16, 32)


def ms() -> float:
    return time.monotonic() * 1000


async def main() -> None:
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Control del Reactor - prototipo móvil")
    reloj = pygame.time.Clock()
    letra = pygame.font.Font(None, 28)

    url = url_del_servidor()
    conexion = crear_conexion(url)
    await conexion.conectar()
    fuentes = [Teclado(), Tactil(ANCHO, ALTO)]

    seq = 0
    mi_id = None
    jugadores: list[dict] = []
    latencia = None
    ultimo_ping = 0.0
    ultimo_origen = "-"

    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                return
            for fuente in fuentes:
                fuente.procesar(evento)

        for fuente in fuentes:
            for control, estado in fuente.obtener():
                seq += 1
                ultimo_origen = fuente.origen
                conexion.enviar(
                    {
                        "tipo": "entrada",
                        "control": control,
                        "estado": estado,
                        "origen": fuente.origen,
                        "seq": seq,
                    }
                )

        if conexion.estado == "abierta" and ms() - ultimo_ping > 1000:
            ultimo_ping = ms()
            conexion.enviar({"tipo": "ping", "t": ultimo_ping})

        for mensaje in conexion.recibir():
            tipo = mensaje.get("tipo")
            if tipo == "bienvenida":
                mi_id = mensaje["id"]
            elif tipo == "estado":
                jugadores = mensaje["jugadores"]
            elif tipo == "pong" and mensaje.get("t") is not None:
                latencia = ms() - float(mensaje["t"])

        pantalla.fill(FONDO)
        pygame.draw.rect(pantalla, (40, 60, 110), (10, 10, ANCHO - 20, ALTO - 20), 2)
        for j in jugadores:
            centro = (int(j["x"]), int(j["y"]))
            radio = 26 if j.get("accion") else 18
            pygame.draw.circle(pantalla, pygame.Color(j["color"]), centro, radio)
            if j["id"] == mi_id:
                pygame.draw.circle(pantalla, (255, 255, 255), centro, radio + 4, 2)
            nombre = letra.render(f"J{j['id']} ({j['origen']})", True, (220, 220, 220))
            pantalla.blit(nombre, (centro[0] - nombre.get_width() // 2, centro[1] - 46))

        lineas = [
            f"Plataforma: {'navegador (pygbag)' if EN_NAVEGADOR else 'escritorio'}",
            f"Servidor: {url}",
            f"Conexión: {conexion.estado}   Jugadores: {len(jugadores)}",
            f"Latencia ida y vuelta: {f'{latencia:.0f} ms' if latencia is not None else '-'}",
            f"Última entrada desde: {ultimo_origen}",
        ]
        for i, texto in enumerate(lineas):
            pantalla.blit(letra.render(texto, True, (200, 200, 200)), (24, 22 + i * 26))
        for fuente in fuentes:
            fuente.dibujar(pantalla)

        pygame.display.flip()
        reloj.tick(60)
        await asyncio.sleep(0)  # obligatorio en pygbag: le devuelve el control al navegador


asyncio.run(main())
