"""Llamadas del cliente al backend (REST).

Todas las funciones son `async`: se usan con `await` desde una tarea (ver las pantallas), así la
ventana no se congela mientras responde el servidor y el mismo código corre en el navegador.
"""

from src.config import SERVER_URL
from src.red import ErrorDeRed, Respuesta, solicitar


class ApiError(Exception):
    """El servidor respondió con un error o no se pudo contactar."""


def _mensaje_de_error(respuesta: Respuesta) -> str:
    datos = respuesta.datos
    detalle = datos.get("detail") if isinstance(datos, dict) else None
    if isinstance(detalle, str):
        return detalle
    # los 422 de FastAPI vienen como lista
    if isinstance(detalle, list) and detalle and isinstance(detalle[0], dict):
        mensaje = str(detalle[0].get("msg", ""))
        return mensaje.removeprefix("Value error, ") or f"Error {respuesta.estado}"
    return f"Error {respuesta.estado}"


async def _enviar(metodo: str, ruta: str, cuerpo: dict | None = None) -> dict:
    try:
        respuesta = await solicitar(metodo, f"{SERVER_URL}{ruta}", cuerpo)
    except ErrorDeRed as error:
        raise ApiError("Sin conexión con el servidor") from error
    if not respuesta.ok:
        raise ApiError(_mensaje_de_error(respuesta))
    return respuesta.datos


async def registrar_usuario(nombre_usuario: str, correo: str, contrasena: str) -> dict:
    return await _enviar(
        "POST",
        "/auth/registro",
        {"nombre_usuario": nombre_usuario, "correo": correo, "contrasena": contrasena},
    )


async def crear_partida(creador_id: int, escenario: str | None = None) -> dict:
    return await _enviar("POST", "/partidas", {"creador_id": creador_id, "escenario": escenario})


async def estado_servidor() -> str:
    """Texto para mostrar en pantalla según responda /health."""
    try:
        respuesta = await solicitar("GET", f"{SERVER_URL}/health", timeout=2)
    except ErrorDeRed:
        return "Servidor: sin conexión"
    return "Servidor: conectado" if respuesta.ok else "Servidor: error"
