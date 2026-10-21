"""Controles del jugador durante la partida: junta las fuentes de entrada y envía sus cambios.

Cada cambio de cualquier fuente (teclado, táctil, Arduino o simulador) se envía al servidor con el
mensaje `entrada` del contrato de hardware, con un `seq` creciente por conexión. Los avisos de
estado del dispositivo (`dispositivo`) del control físico también se reenvían.

Uso desde la pantalla de juego:

    controles = ControlesJugador(crear_fuentes(ancho, alto), canal.enviar)
    # por cada evento de pygame:
    controles.procesar(evento)
    # una vez por cuadro:
    controles.actualizar()
    controles.dibujar(pantalla)   # botones táctiles, si hay
    # al salir de la partida:
    controles.cerrar()
"""

import sys
from collections.abc import Callable, Iterable
from typing import Any

from .base import FuenteEntrada
from .serial_entrada import EntradaSerial
from .tactil import Tactil
from .teclado import Teclado


def crear_fuentes(
    ancho: int,
    alto: int,
    puerto_control: str | None = None,
    en_navegador: bool | None = None,
) -> list[FuenteEntrada]:
    """Fuentes según la plataforma (patrón Factory).

    - Siempre el teclado.
    - Botones táctiles solo en el navegador (versión móvil, ADR 0002).
    - Control físico o simulador solo en escritorio y si se indicó un puerto
      (`CONTROL_PUERTO`, por ejemplo `COM3` o `socket://localhost:7777`).
    """
    if en_navegador is None:
        en_navegador = sys.platform == "emscripten"
    fuentes: list[FuenteEntrada] = [Teclado()]
    if en_navegador:
        fuentes.append(Tactil(ancho, alto))
    elif puerto_control:
        fuentes.append(EntradaSerial(puerto_control))
    return fuentes


class ControlesJugador:
    def __init__(self, fuentes: Iterable[FuenteEntrada], enviar: Callable[[dict], Any]) -> None:
        self.fuentes = list(fuentes)
        self._enviar = enviar
        self._seq = 0
        self.ultimo_origen: str | None = None

    def procesar(self, evento: Any) -> None:
        for fuente in self.fuentes:
            fuente.procesar(evento)

    def actualizar(self) -> int:
        """Revisa las fuentes y envía lo nuevo. Devuelve cuántas entradas se enviaron."""
        enviadas = 0
        for fuente in self.fuentes:
            fuente.revisar()
            for control, estado in fuente.obtener():
                self._seq += 1
                self._enviar(
                    {
                        "tipo": "entrada",
                        "control": control,
                        "estado": estado,
                        "origen": fuente.origen,
                        "seq": self._seq,
                    }
                )
                self.ultimo_origen = fuente.origen
                enviadas += 1
            for aviso in fuente.obtener_avisos():
                self._enviar(aviso)
        return enviadas

    def dibujar(self, pantalla: Any) -> None:
        for fuente in self.fuentes:
            fuente.dibujar(pantalla)

    def control_fisico(self) -> EntradaSerial | None:
        """El control físico, si hay, para mostrar su estado en pantalla."""
        return next((f for f in self.fuentes if isinstance(f, EntradaSerial)), None)

    def cerrar(self) -> None:
        for fuente in self.fuentes:
            cerrar = getattr(fuente, "cerrar", None)
            if cerrar is not None:
                cerrar()
