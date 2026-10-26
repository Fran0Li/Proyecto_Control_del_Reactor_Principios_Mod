"""Endpoints de autenticación (Rol A: US-01 a US-06)."""

import logging
import re

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.dependencias import EnviadorDep, SessionDep, UsuarioActual
from app.api.paginas import pagina_simple
from app.repositories import TokenRepository, UsuarioRepository
from app.services.correo import CorreoNoEnviadoError, EnviadorCorreo
from app.services.login_service import (
    CorreoNoVerificadoError,
    CredencialesInvalidasError,
    CuentaBloqueadaError,
    LoginService,
)
from app.services.recuperacion_service import RecuperacionService
from app.services.registro_service import RegistroError, RegistroService
from app.services.tokens_correo import TokenNoValidoError, TokensDeCorreo, TokenVencidoError
from app.services.verificacion_service import VerificacionService

router = APIRouter(prefix="/auth", tags=["autenticación"])
log = logging.getLogger(__name__)

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def contrasena_segura(valor: str) -> str:
    tiene_letra = any(caracter.isalpha() for caracter in valor)
    tiene_numero = any(caracter.isdigit() for caracter in valor)
    if not (tiene_letra and tiene_numero):
        raise ValueError("La contraseña debe tener al menos una letra y un número")
    return valor


class RegistroRequest(BaseModel):
    nombre_usuario: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    correo: str = Field(max_length=120)
    contrasena: str = Field(min_length=8, max_length=128)

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if not PATRON_CORREO.match(valor):
            raise ValueError("El formato del correo no es válido")
        return valor

    @field_validator("contrasena")
    @classmethod
    def validar_contrasena(cls, valor: str) -> str:
        return contrasena_segura(valor)


class UsuarioRegistradoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_usuario: str
    correo: str
    correo_verificado: bool


@router.post(
    "/registro",
    response_model=UsuarioRegistradoResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar(datos: RegistroRequest, db: SessionDep, enviador: EnviadorDep):
    servicio = RegistroService(UsuarioRepository(db))
    try:
        usuario = servicio.registrar(datos.nombre_usuario, datos.correo, datos.contrasena)
    except RegistroError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    try:
        _verificacion(db, enviador).enviar_correo(usuario)
    except CorreoNoEnviadoError as error:
        # la cuenta igual queda creada: desde el juego se puede pedir otro correo
        log.warning("No se pudo enviar el correo de verificación: %s", error)
    return usuario


def _verificacion(db: Session, enviador: EnviadorCorreo) -> VerificacionService:
    return VerificacionService(UsuarioRepository(db), TokensDeCorreo(TokenRepository(db)), enviador)


@router.get("/verificar", response_class=HTMLResponse)
def verificar_correo(token: str, db: SessionDep, enviador: EnviadorDep):
    """Lo abre el jugador desde el enlace del correo, por eso responde una página y no JSON."""
    try:
        _verificacion(db, enviador).verificar(token)
    except TokenVencidoError:
        return pagina_simple("Enlace vencido", "Pedí un correo nuevo desde el juego.", 400)
    except TokenNoValidoError:
        return pagina_simple("Enlace no válido", "El enlace no existe o ya se usó.", 400)
    return pagina_simple("¡Correo verificado!", "Ya podés volver al juego e iniciar sesión.")


class ReenviarRequest(BaseModel):
    correo: str = Field(max_length=120)


@router.post("/reenviar-verificacion", status_code=status.HTTP_202_ACCEPTED)
def reenviar_verificacion(datos: ReenviarRequest, db: SessionDep, enviador: EnviadorDep):
    try:
        _verificacion(db, enviador).reenviar(datos.correo)
    except CorreoNoEnviadoError as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "No se pudo enviar el correo, probá más tarde"
        ) from error
    return {"detail": "Si la cuenta existe y falta verificarla, te mandamos un correo nuevo"}


class LoginRequest(BaseModel):
    usuario: str = Field(min_length=1, max_length=120)  # nombre de usuario o correo
    contrasena: str = Field(min_length=1, max_length=128)


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_usuario: str
    correo: str


class SesionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse


@router.post("/login", response_model=SesionResponse)
def iniciar_sesion(datos: LoginRequest, db: SessionDep):
    servicio = LoginService(UsuarioRepository(db))
    try:
        usuario, token = servicio.iniciar_sesion(datos.usuario, datos.contrasena)
    except CredencialesInvalidasError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error)) from error
    except CorreoNoVerificadoError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    except CuentaBloqueadaError as error:
        raise HTTPException(status.HTTP_423_LOCKED, str(error)) from error
    return SesionResponse(access_token=token, usuario=UsuarioResponse.model_validate(usuario))


@router.get("/yo", response_model=UsuarioResponse)
def usuario_en_sesion(usuario: UsuarioActual):
    return usuario


def _recuperacion(db: Session, enviador: EnviadorCorreo) -> RecuperacionService:
    return RecuperacionService(UsuarioRepository(db), TokensDeCorreo(TokenRepository(db)), enviador)


class RecuperarRequest(BaseModel):
    correo: str = Field(max_length=120)


@router.post("/recuperar", status_code=status.HTTP_202_ACCEPTED)
def solicitar_recuperacion(datos: RecuperarRequest, db: SessionDep, enviador: EnviadorDep):
    try:
        _recuperacion(db, enviador).solicitar(datos.correo)
    except CorreoNoEnviadoError as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "No se pudo enviar el correo, probá más tarde"
        ) from error
    return {"detail": "Si el correo está registrado, te mandamos un código"}


class RestablecerRequest(BaseModel):
    correo: str = Field(max_length=120)
    codigo: str = Field(min_length=1, max_length=20)
    contrasena: str = Field(min_length=8, max_length=128)

    @field_validator("contrasena")
    @classmethod
    def validar_contrasena(cls, valor: str) -> str:
        return contrasena_segura(valor)


@router.post("/restablecer")
def restablecer_contrasena(datos: RestablecerRequest, db: SessionDep, enviador: EnviadorDep):
    try:
        _recuperacion(db, enviador).restablecer(datos.correo, datos.codigo, datos.contrasena)
    except TokenVencidoError as error:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "El código venció, pedí uno nuevo"
        ) from error
    except TokenNoValidoError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El código no es válido") from error
    return {"detail": "Contraseña cambiada. Ya podés iniciar sesión"}
