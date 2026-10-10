"""Fuente de entrada del control físico: Arduino por USB o el simulador por socket local.

Lee el puerto sin bloquear (una vez por frame), interpreta las líneas del contrato y las convierte
en entradas. Implementa las reglas de desconexión del contrato:
- si no llega nada durante 3 s, suelta los controles presionados y avisa "desconectado";
- reintenta abrir el puerto cada 2 s y avisa "conectado" al recibir datos válidos.

El puerto se abre con pyserial, que acepta tanto "COM3" o "/dev/ttyUSB0" como
"socket://localhost:7777" (simulador). pyserial se importa dentro de la función para que pygbag
no intente instalarlo en el navegador (ADR 0002).
"""

import logging
import time
from collections.abc import Callable
from typing import Any

from .base import FuenteEntrada
from .protocolo_serial import Boton, Saludo, interpretar_linea

log = logging.getLogger(__name__)

BAUDIOS = 115200
SIN_DATOS_S = 3.0  # sin mensajes durante este tiempo = desconectado
REINTENTO_S = 2.0  # cada cuánto se intenta abrir el puerto otra vez
GRACIA_APERTURA_S = 2.0  # el Arduino Uno se reinicia al abrir el puerto y tarda en mandar HELLO
MAX_LINEA = 128


def abrir_con_pyserial(puerto: str) -> Any:
    import serial  # solo existe en escritorio

    return serial.serial_for_url(puerto, baudrate=BAUDIOS, timeout=0)


class EntradaSerial(FuenteEntrada):
    def __init__(
        self,
        puerto: str,
        abrir: Callable[[str], Any] = abrir_con_pyserial,
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__()
        self.puerto = puerto
        self.origen = "simulador" if puerto.startswith("socket://") else "hardware"
        self.estado = "desconectado"  # desconectado | abierto | conectado
        self.id_dispositivo: str | None = None
        self.lineas_invalidas = 0
        self._abrir = abrir
        self._reloj = reloj
        self._conexion: Any = None
        self._buffer = b""
        self._presionados: set[str] = set()
        self._avisos: list[dict] = []
        self._ultimo_dato = 0.0
        self._ultimo_intento = float("-inf")

    # ---- interfaz FuenteEntrada -------------------------------------------------------------

    def revisar(self) -> None:
        ahora = self._reloj()
        if self._conexion is None:
            if ahora - self._ultimo_intento >= REINTENTO_S:
                self._intentar_abrir(ahora)
            return

        try:
            datos = self._conexion.read(4096)
        except Exception as error:  # noqa: BLE001 - cable desconectado, socket cerrado, etc.
            self._desconectar(ahora, f"error de lectura: {error.__class__.__name__}")
            return

        if datos:
            self._ultimo_dato = ahora
            self._procesar_bytes(datos)
        elif ahora - self._ultimo_dato > SIN_DATOS_S:
            self._desconectar(ahora, "sin mensajes del control")

    def obtener_avisos(self) -> list[dict]:
        avisos, self._avisos = self._avisos, []
        return avisos

    def cerrar(self) -> None:
        self._desconectar(self._reloj(), "cerrado por el cliente")

    # ---- interno ----------------------------------------------------------------------------

    def _intentar_abrir(self, ahora: float) -> None:
        self._ultimo_intento = ahora
        try:
            self._conexion = self._abrir(self.puerto)
        except Exception as error:  # noqa: BLE001
            log.debug("No se pudo abrir %s: %s", self.puerto, error)
            return
        self.estado = "abierto"
        self._buffer = b""
        self._ultimo_dato = ahora + GRACIA_APERTURA_S
        log.info("Puerto %s abierto, esperando al control", self.puerto)

    def _procesar_bytes(self, datos: bytes) -> None:
        self._buffer += datos
        *lineas, self._buffer = self._buffer.split(b"\n")
        if len(self._buffer) > MAX_LINEA:  # basura sin salto de línea
            self._buffer = b""
            self.lineas_invalidas += 1
        for cruda in lineas:
            texto = cruda.decode("ascii", errors="replace").strip()
            if texto:
                self._procesar_linea(texto)

    def _procesar_linea(self, texto: str) -> None:
        mensaje = interpretar_linea(texto)
        if mensaje is None:
            self.lineas_invalidas += 1
            log.warning("Línea inválida del control descartada: %r", texto)
            return

        if isinstance(mensaje, Saludo):
            self.id_dispositivo = mensaje.id_dispositivo
        if self.estado != "conectado":
            self.estado = "conectado"
            self._avisos.append(self._aviso("conectado"))

        if isinstance(mensaje, Boton):
            if mensaje.estado == "presionado" and mensaje.control not in self._presionados:
                self._presionados.add(mensaje.control)
                self._pendientes.append((mensaje.control, "presionado"))
            elif mensaje.estado == "liberado" and mensaje.control in self._presionados:
                self._presionados.discard(mensaje.control)
                self._pendientes.append((mensaje.control, "liberado"))

    def _desconectar(self, ahora: float, motivo: str) -> None:
        for control in sorted(self._presionados):
            self._pendientes.append((control, "liberado"))
        self._presionados.clear()
        if self._conexion is not None:
            try:
                self._conexion.close()
            except Exception:  # noqa: BLE001
                pass
        self._conexion = None
        self._ultimo_intento = ahora
        if self.estado == "conectado":
            self._avisos.append(self._aviso("desconectado"))
            log.warning("Control desconectado: %s", motivo)
        self.estado = "desconectado"

    def _aviso(self, estado: str) -> dict:
        return {"tipo": "dispositivo", "estado": estado, "id": self.id_dispositivo or "?"}
