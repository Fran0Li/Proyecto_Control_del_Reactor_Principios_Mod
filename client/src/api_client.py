"""Llamadas del cliente al backend (REST).

Todas las funciones son `async`: se usan con `await` desde una tarea (ver las pantallas), así la
ventana no se congela mientras responde el servidor y el mismo código corre en el navegador.
"""

from typing import Any

from src.config import SERVER_URL
from src.red import ErrorDeRed, Respuesta, solicitar


class ApiError(Exception):
    """El servidor respondió con un error o no se pudo contactar."""

    def __init__(self, mensaje: str, estado: int | None = None) -> None:
        super().__init__(mensaje)
        self.estado = estado  # código HTTP, o None si no hubo respuesta


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


async def _enviar(
    metodo: str, ruta: str, cuerpo: dict | None = None, token: str | None = None
) -> Any:
    extra = {"headers": {"Authorization": f"Bearer {token}"}} if token else {}
    try:
        respuesta = await solicitar(metodo, f"{SERVER_URL}{ruta}", cuerpo, **extra)
    except ErrorDeRed as error:
        raise ApiError("Sin conexión con el servidor") from error
    if not respuesta.ok:
        raise ApiError(_mensaje_de_error(respuesta), respuesta.estado)
    return respuesta.datos


async def registrar_usuario(nombre_usuario: str, correo: str, contrasena: str) -> dict:
    return await _enviar(
        "POST",
        "/auth/registro",
        {"nombre_usuario": nombre_usuario, "correo": correo, "contrasena": contrasena},
    )


async def iniciar_sesion(usuario: str, contrasena: str) -> dict:
    """Devuelve {"access_token": ..., "usuario": {...}}."""
    return await _enviar("POST", "/auth/login", {"usuario": usuario, "contrasena": contrasena})


async def reenviar_verificacion(correo: str) -> dict:
    return await _enviar("POST", "/auth/reenviar-verificacion", {"correo": correo})


async def solicitar_recuperacion(correo: str) -> dict:
    return await _enviar("POST", "/auth/recuperar", {"correo": correo})


async def restablecer_contrasena(correo: str, codigo: str, contrasena: str) -> dict:
    return await _enviar(
        "POST",
        "/auth/restablecer",
        {"correo": correo, "codigo": codigo, "contrasena": contrasena},
    )


def url_login_google(sesion_id: str) -> str:
    return f"{SERVER_URL}/auth/google/iniciar?sesion={sesion_id}"


async def resultado_login_google(sesion_id: str) -> dict | None:
    """Lo mismo que el login normal, o None si el jugador todavía no termina en el navegador."""
    try:
        respuesta = await solicitar("GET", f"{SERVER_URL}/auth/google/resultado?sesion={sesion_id}")
    except ErrorDeRed as error:
        raise ApiError("Sin conexión con el servidor") from error
    if respuesta.estado == 202:
        return None
    if not respuesta.ok:
        raise ApiError(_mensaje_de_error(respuesta), respuesta.estado)
    return respuesta.datos


async def obtener_perfil(token: str) -> dict:
    return await _enviar("GET", "/perfil", token=token)


async def editar_perfil(token: str, cambios: dict) -> dict:
    return await _enviar("PATCH", "/perfil", cambios, token=token)


async def crear_partida(token: str, escenario: str | None = None) -> dict:
    """El servidor toma al creador del token."""
    return await _enviar("POST", "/partidas", {"escenario": escenario}, token=token)



async def listar_partidas_disponibles() -> list[dict]:
    datos = await _enviar("GET", "/partidas")
    return datos if isinstance(datos, list) else []


async def unirse_a_partida(partida_id: int, token: str) -> dict:
    """Se une el jugador del token."""
    return await _enviar("POST", f"/partidas/{partida_id}/unirse", token=token)


async def iniciar_partida(partida_id: int, token: str) -> dict:
    """Solo el creador puede iniciarla (US-17); el servidor avisa a todos por el canal."""
    return await _enviar("POST", f"/partidas/{partida_id}/iniciar", token=token)


async def obtener_resultado(partida_id: int, token: str) -> dict:
    """Podio y estadísticas de una partida terminada (US-18). Da 409 mientras se guarda."""
    return await _enviar("GET", f"/partidas/{partida_id}/resultado", token=token)


async def obtener_ranking(token: str) -> dict:
    """{"top": [...10 mejores], "yo": puesto propio o None} (US-19)."""
    return await _enviar("GET", "/ranking", token=token)


async def obtener_historial(token: str) -> dict:
    """{"resumen": {...}, "partidas": [...]} del jugador conectado (US-20)."""
    return await _enviar("GET", "/historial", token=token)


async def obtener_logros(token: str) -> list[dict]:
    datos = await _enviar("GET", "/logros", token=token)
    return datos if isinstance(datos, list) else []


# administración (US-28): el servidor responde 403 si la cuenta no es de administrador


async def admin_estadisticas(token: str) -> dict:
    return await _enviar("GET", "/admin/estadisticas", token=token)


async def admin_usuarios(token: str) -> list[dict]:
    return await _enviar("GET", "/admin/usuarios", token=token)


async def admin_partidas(token: str) -> list[dict]:
    return await _enviar("GET", "/admin/partidas", token=token)


async def admin_bloquear(token: str, usuario_id: int, bloquear: bool) -> dict:
    accion = "bloquear" if bloquear else "desbloquear"
    return await _enviar("POST", f"/admin/usuarios/{usuario_id}/{accion}", token=token)


async def admin_cerrar_partida(token: str, partida_id: int) -> dict:
    return await _enviar("POST", f"/admin/partidas/{partida_id}/cerrar", token=token)


async def estado_servidor() -> str:
    """Texto para mostrar en pantalla según responda /health."""
    try:
        respuesta = await solicitar("GET", f"{SERVER_URL}/health", timeout=2)
    except ErrorDeRed:
        return "Servidor: sin conexión"
    return "Servidor: conectado" if respuesta.ok else "Servidor: error"
