"""Llamadas del cliente al backend (REST)."""

import requests

from src.config import SERVER_URL

TIMEOUT_SEGUNDOS = 3


class ApiError(Exception):
    """El servidor respondió con un error o no se pudo contactar."""


def _mensaje_de_error(respuesta: requests.Response) -> str:
    try:
        datos = respuesta.json()
    except ValueError:
        datos = None
    detalle = datos.get("detail") if isinstance(datos, dict) else None
    if isinstance(detalle, str):
        return detalle
    return f"Error {respuesta.status_code}"


def crear_partida(creador_id: int, escenario: str | None = None) -> dict:
    try:
        respuesta = requests.post(
            f"{SERVER_URL}/partidas",
            json={"creador_id": creador_id, "escenario": escenario},
            timeout=TIMEOUT_SEGUNDOS,
        )
    except requests.RequestException as error:
        raise ApiError("Sin conexión con el servidor") from error
    if not respuesta.ok:
        raise ApiError(_mensaje_de_error(respuesta))
    return respuesta.json()