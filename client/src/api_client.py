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
    # Errores de validación de FastAPI (422): lista de {"msg": ...}
    if isinstance(detalle, list) and detalle and isinstance(detalle[0], dict):
        mensaje = str(detalle[0].get("msg", ""))
        return mensaje.removeprefix("Value error, ") or f"Error {respuesta.status_code}"
    return f"Error {respuesta.status_code}"


def registrar_usuario(nombre_usuario: str, correo: str, contrasena: str) -> dict:
    try:
        respuesta = requests.post(
            f"{SERVER_URL}/auth/registro",
            json={"nombre_usuario": nombre_usuario, "correo": correo, "contrasena": contrasena},
            timeout=TIMEOUT_SEGUNDOS,
        )
    except requests.RequestException as error:
        raise ApiError("Sin conexión con el servidor") from error
    if not respuesta.ok:
        raise ApiError(_mensaje_de_error(respuesta))
    return respuesta.json()


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