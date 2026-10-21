"""Fuentes de entrada del cliente (ADR 0002 y ADR 0003, patrón Adapter).

- base.FuenteEntrada: interfaz común.
- teclado.Teclado: flechas o WASD y espacio.
- tactil.Tactil: cruceta y botón de acción en pantalla (versión móvil).
- serial_entrada.EntradaSerial: control físico (Arduino) o simulador.
- controles.ControlesJugador: junta las fuentes y envía el mensaje `entrada` al servidor.
"""

from .base import CONTROLES, ESTADOS, FuenteEntrada
from .controles import ControlesJugador, crear_fuentes
from .serial_entrada import EntradaSerial
from .tactil import Tactil
from .teclado import Teclado

__all__ = [
    "CONTROLES",
    "ESTADOS",
    "ControlesJugador",
    "EntradaSerial",
    "FuenteEntrada",
    "Tactil",
    "Teclado",
    "crear_fuentes",
]
