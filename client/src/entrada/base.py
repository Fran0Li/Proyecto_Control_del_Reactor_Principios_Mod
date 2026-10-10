"""Interfaz común de las fuentes de entrada del cliente (ADR 0002, patrón Adapter).

Teclado, botones táctiles y control físico (Arduino o simulador) entregan lo mismo: pares
(control, estado) con los valores del contrato de hardware. El cliente los convierte en el
mensaje "entrada" sin saber de qué fuente vienen.
"""

from typing import Any

CONTROLES = ("arriba", "abajo", "izquierda", "derecha", "accion")
ESTADOS = ("presionado", "liberado")


class FuenteEntrada:
    origen = "?"  # valor del campo "origen" del contrato

    def __init__(self) -> None:
        self._pendientes: list[tuple[str, str]] = []

    def procesar(self, evento: Any) -> None:
        """Recibe cada evento de pygame. Las fuentes que no usan eventos lo ignoran."""

    def revisar(self) -> None:
        """Se llama una vez por frame (leer el puerto, corregir estados perdidos, etc.)."""

    def obtener(self) -> list[tuple[str, str]]:
        """Entradas acumuladas desde la última llamada."""
        pendientes, self._pendientes = self._pendientes, []
        return pendientes

    def obtener_avisos(self) -> list[dict]:
        """Mensajes extra para el servidor, por ejemplo el estado del dispositivo."""
        return []

    def dibujar(self, pantalla: Any) -> None:
        """Opcional: para fuentes con interfaz visual (botones táctiles)."""
