"""Fuentes de entrada del cliente (ADR 0002).

- base.FuenteEntrada: interfaz común.
- serial_entrada.EntradaSerial: control físico (Arduino) o simulador.
- Teclado y táctil: se agregan con la misma interfaz (ver prototipos/cliente-movil/entrada.py).
"""

from .base import CONTROLES, ESTADOS, FuenteEntrada
from .serial_entrada import EntradaSerial

__all__ = ["CONTROLES", "ESTADOS", "EntradaSerial", "FuenteEntrada"]
