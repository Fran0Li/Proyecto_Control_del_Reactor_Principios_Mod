"""Pruebas de aceptación del control físico, sin la ventana del juego (CP-274, CP-285 y CP-301).

Hace de cliente: inicia sesión, crea una partida, lee el Arduino con el mismo adaptador del juego
(`EntradaSerial`) y manda las entradas por el WebSocket. Con eso mide y muestra:

- **Latencia (CP-274):** desde que la PC lee la línea `BTN ... PRESS` del Arduino hasta que el
  servidor le devuelve al cliente la posición nueva en esa dirección.
- **Desconexión (CP-285):** cuándo se pierde y se recupera el control y si el jugador se detiene.
- **Extracción (CP-301):** distancia al reactor, puntaje y energía del reactor al presionar ACCIÓN.

Uso (backend corriendo y el Monitor Serie del Arduino IDE cerrado):

    python probar_control.py                  # COM5, backend local
    python probar_control.py --puerto COM3
    python probar_control.py --puerto socket://localhost:7777   # con el simulador
    python probar_control.py --partida 7      # si ya estás en la partida 7

Pide el usuario y la contraseña de una cuenta verificada (la contraseña no se muestra).
Ctrl+C termina, imprime el resumen y guarda las mediciones en `latencia_<fecha>.csv`.
"""

import argparse
import asyncio
import csv
import getpass
import math
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime

from src import api_client
from src.entrada import ControlesJugador
from src.entrada.serial_entrada import EntradaSerial
from src.realtime_client import CanalPartida

LIMITE_MS = 500  # criterio de la US-10 y RNF-02
SIN_MOVIMIENTO_S = 1.0  # si en este tiempo no se movió, se descarta (pared u obstáculo)
DIRECCIONES = {"arriba": (0, -1), "abajo": (0, 1), "izquierda": (-1, 0), "derecha": (1, 0)}
LIMPIAR = (
    "docker compose exec db psql -U reactor -d reactor -c "
    '"DELETE FROM participaciones; DELETE FROM partidas;"'
)


def hora() -> str:
    return datetime.now().strftime("%H:%M:%S")


@dataclass
class Pendiente:
    control: str
    t0: float
    x: float
    y: float


@dataclass
class Medicion:
    n: int
    control: str
    ms: float


@dataclass
class Prueba:
    jugador_id: int
    mediciones: list[Medicion] = field(default_factory=list)
    descartadas: int = 0
    pendiente: Pendiente | None = None
    accion: tuple[float, int, int] | None = None  # (t0, puntaje, energía) al presionar ACCIÓN
    estado: dict | None = None
    ultimo_aviso_pos = 0.0

    # ---- lo que llega del servidor -----------------------------------------------------------

    def yo(self) -> dict | None:
        if self.estado is None:
            return None
        return next(
            (j for j in self.estado["jugadores"] if j["jugador_id"] == self.jugador_id), None
        )

    def distancia_al_reactor(self) -> tuple[float, bool] | None:
        yo = self.yo()
        if yo is None or self.estado is None:
            return None
        arena = self.estado["arena"]
        reactor = arena["reactor"]
        distancia = math.hypot(yo["x"] - reactor["x"], yo["y"] - reactor["y"])
        return distancia, distancia <= reactor["radio"] + arena["radio"]

    def energia(self) -> int:
        if self.estado is None:
            return 0
        return int(self.estado.get("reactor", {}).get("energia", 0))

    def recibir_estado(self, estado: dict, ahora: float) -> None:
        self.estado = estado
        yo = self.yo()
        if yo is None:
            return
        self._revisar_movimiento(yo, ahora)
        self._revisar_accion(yo, ahora)
        if ahora - self.ultimo_aviso_pos >= 1.0:  # para guiarse sin ventana, una vez por segundo
            self.ultimo_aviso_pos = ahora
            distancia, tocando = self.distancia_al_reactor() or (0.0, False)
            print(
                f"  pos ({yo['x']}, {yo['y']})  reactor a {distancia:.0f} px"
                f"{' (TOCANDO)' if tocando else ''}  puntaje {yo['puntaje']}"
                f"  energía del reactor {self.energia()}"
            )

    def _revisar_movimiento(self, yo: dict, ahora: float) -> None:
        p = self.pendiente
        if p is None:
            return
        dx, dy = DIRECCIONES[p.control]
        if (yo["x"] - p.x) * dx > 0 or (yo["y"] - p.y) * dy > 0:
            ms = (ahora - p.t0) * 1000
            self.mediciones.append(Medicion(len(self.mediciones) + 1, p.control, ms))
            marca = "OK" if ms < LIMITE_MS else "NO PASA"
            print(f"[{hora()}] #{len(self.mediciones)} {p.control}: {ms:.0f} ms  {marca}")
            self.pendiente = None

    def _revisar_accion(self, yo: dict, ahora: float) -> None:
        if self.accion is None:
            return
        t0, puntaje, energia = self.accion
        if yo["puntaje"] != puntaje or ahora - t0 > 0.5:
            sumo = yo["puntaje"] - puntaje
            print(
                f"[{hora()}] ACCIÓN: puntaje {puntaje} -> {yo['puntaje']} (+{sumo}), "
                f"reactor {energia} -> {self.energia()}"
            )
            self.accion = None

    # ---- lo que se manda al servidor ---------------------------------------------------------

    def enviado(self, mensaje: dict, ahora: float) -> None:
        if mensaje.get("tipo") == "dispositivo":
            print(f"[{hora()}] Control {mensaje['estado'].upper()} ({mensaje['id']})")
            return
        control, estado = mensaje["control"], mensaje["estado"]
        yo = self.yo()
        if estado != "presionado" or yo is None:
            if control in DIRECCIONES and estado == "liberado":
                self.pendiente = None
            return
        if control == "accion":
            distancia, tocando = self.distancia_al_reactor() or (0.0, False)
            lugar = "tocando el reactor" if tocando else f"lejos del reactor ({distancia:.0f} px)"
            print(f"[{hora()}] ACCIÓN presionada, {lugar}")
            self.accion = (ahora, yo["puntaje"], self.energia())
        elif control in DIRECCIONES:
            self.pendiente = Pendiente(control, ahora, yo["x"], yo["y"])

    def vencer(self, ahora: float) -> None:
        if self.pendiente is not None and ahora - self.pendiente.t0 > SIN_MOVIMIENTO_S:
            print(f"[{hora()}] {self.pendiente.control}: no se movió (¿pared u obstáculo?)")
            self.descartadas += 1
            self.pendiente = None

    # ---- resumen ----------------------------------------------------------------------------

    def resumen(self) -> None:
        print("\n===== Resumen de latencia (CP-274) =====")
        if not self.mediciones:
            print("Sin mediciones.")
            return
        valores = sorted(m.ms for m in self.mediciones)
        p95 = valores[min(len(valores) - 1, math.ceil(0.95 * len(valores)) - 1)]
        print(f"Mediciones: {len(valores)} (descartadas sin movimiento: {self.descartadas})")
        print(
            f"Promedio {statistics.mean(valores):.0f} ms | mediana {statistics.median(valores):.0f}"
            f" ms | p95 {p95:.0f} ms | mínimo {valores[0]:.0f} ms | máximo {valores[-1]:.0f} ms"
        )
        print(
            "Sin contar: antirrebote del firmware (20 ms), USB (~1 ms) y dibujar el cuadro"
            " (hasta 17 ms a 60 fps)."
        )
        veredicto = "PASA" if valores[-1] + 40 < LIMITE_MS else "NO PASA"
        print(f"Máximo + 40 ms de margen = {valores[-1] + 40:.0f} ms -> {veredicto} (< 500 ms)")
        archivo = f"latencia_{datetime.now():%Y%m%d_%H%M}.csv"
        with open(archivo, "w", newline="", encoding="utf-8") as f:
            escritor = csv.writer(f)
            escritor.writerow(["n", "control", "ms"])
            escritor.writerows((m.n, m.control, f"{m.ms:.1f}") for m in self.mediciones)
        print(f"Guardado en {archivo}")


async def preparar(usuario: str | None, partida_id: int | None) -> tuple[dict, int]:
    usuario = usuario or input("Usuario o correo: ")
    contrasena = getpass.getpass("Contraseña (no se ve al escribir): ")
    sesion = await api_client.iniciar_sesion(usuario, contrasena)
    if partida_id is not None:  # una partida en la que ya está
        return sesion, partida_id
    try:
        partida = await api_client.crear_partida(sesion["access_token"])
    except api_client.ApiError as error:
        if error.estado != 409:
            raise
        en_espera = [p["id"] for p in await api_client.listar_partidas_disponibles()]
        print(f"\n{error}.")
        print(f"Partidas en espera: {en_espera}. Si una es tuya: --partida <número>.")
        print(f"O cerrá las partidas viejas, en la raíz del repo:\n  {LIMPIAR}")
        sys.exit(1)
    return sesion, partida["id"]


async def principal(puerto: str, usuario: str | None, partida: int | None) -> None:
    sesion, partida_id = await preparar(usuario, partida)
    prueba = Prueba(sesion["usuario"]["id"])
    canal = CanalPartida(partida_id, sesion["access_token"])
    await canal.conectar()

    def enviar(mensaje: dict) -> None:
        prueba.enviado(mensaje, time.perf_counter())
        canal.enviar(mensaje)

    serial = EntradaSerial(puerto)
    controles = ControlesJugador([serial], enviar)
    print(f"\nPartida #{partida_id}, jugador {prueba.jugador_id}, control en {puerto}.")
    print("El reactor está al centro (480, 270). Ctrl+C para terminar.\n")
    try:
        while True:
            controles.actualizar()  # lee el Arduino (no bloquea) y manda las entradas
            for mensaje in canal.leer_mensajes():
                if mensaje.get("tipo") == "estado":
                    prueba.recibir_estado(mensaje, time.perf_counter())
            prueba.vencer(time.perf_counter())
            if canal.estado.startswith("error") or canal.estado == "cerrada":
                print(f"Se cerró el canal con el servidor: {canal.estado}")
                break
            await asyncio.sleep(0.001)
    finally:
        controles.cerrar()
        canal.cerrar()
        prueba.resumen()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--puerto", default="COM5", help="COM5, COM3 o socket://localhost:7777")
    parser.add_argument("--usuario", help="usuario o correo (si no, lo pregunta)")
    parser.add_argument("--partida", type=int, help="usar una partida en la que ya estás")
    args = parser.parse_args()
    try:
        asyncio.run(principal(args.puerto, args.usuario, args.partida))
    except KeyboardInterrupt:
        pass
    except api_client.ApiError as error:
        print(f"Error del servidor: {error}")


if __name__ == "__main__":
    main()
