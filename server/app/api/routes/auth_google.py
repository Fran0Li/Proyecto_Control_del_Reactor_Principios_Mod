"""Login con Google (US-04).

1. El juego abre en el navegador `/auth/google/iniciar?sesion=<id al azar>`.
2. El servidor manda al jugador a Google; Google lo devuelve a `/auth/google/callback`.
3. El servidor crea o vincula la cuenta y deja el token guardado con ese id de sesión.
4. Mientras tanto el juego pregunta por `/auth/google/resultado?sesion=<id>` hasta recibirlo.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.dependencias import SessionDep
from app.api.paginas import pagina_simple
from app.core.security import crear_token_acceso
from app.repositories import UsuarioRepository
from app.services.google_oauth import GoogleError, ProveedorGoogle, crear_proveedor_google
from app.services.login_social_service import CorreoGoogleSinVerificarError, LoginSocialService
from app.services.sesiones_google import sesiones_google

router = APIRouter(prefix="/auth/google", tags=["autenticación"])

SesionId = Annotated[str, Query(pattern=r"^[A-Za-z0-9_-]{16,64}$")]


def get_proveedor_google() -> ProveedorGoogle:
    return crear_proveedor_google()


ProveedorDep = Annotated[ProveedorGoogle, Depends(get_proveedor_google)]


@router.get("/iniciar")
def iniciar(sesion: SesionId, proveedor: ProveedorDep):
    if not proveedor.configurado:
        return pagina_simple(
            "Login con Google no disponible",
            "Falta configurar GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET en el servidor.",
            503,
        )
    return RedirectResponse(proveedor.url_autorizacion(sesion))


@router.get("/callback")
def callback(
    db: SessionDep,
    proveedor: ProveedorDep,
    state: str = "",
    code: str | None = None,
    error: str | None = None,
):
    if error or not code:
        return _fallo(state, "Se canceló el login con Google")
    try:
        perfil = proveedor.obtener_perfil(code)
        usuario = LoginSocialService(UsuarioRepository(db)).entrar_con_google(perfil)
    except (GoogleError, CorreoGoogleSinVerificarError) as fallo:
        return _fallo(state, str(fallo))

    sesiones_google.guardar(
        state,
        {
            "access_token": crear_token_acceso(usuario.id, usuario.version_sesion),
            "token_type": "bearer",
            "usuario": {
                "id": usuario.id,
                "nombre_usuario": usuario.nombre_usuario,
                "correo": usuario.correo,
            },
        },
    )
    return pagina_simple("¡Listo!", "Ya podés cerrar esta pestaña y volver al juego.")


def _fallo(sesion_id: str, mensaje: str):
    sesiones_google.guardar(sesion_id, {"error": mensaje})
    texto = f"{mensaje}. Volvé al juego e intentalo de nuevo."
    return pagina_simple("No se pudo entrar", texto, 400)


@router.get("/resultado")
def resultado(sesion: SesionId):
    datos = sesiones_google.tomar(sesion)
    if datos is None:
        return JSONResponse({"detail": "Esperando el login en el navegador"}, status_code=202)
    if "error" in datos:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, datos["error"])
    return datos
