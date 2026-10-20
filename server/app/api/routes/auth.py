"""Endpoints de autenticación (Rol A: US-01 a US-06)."""

import re

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.dependencias import SessionDep, UsuarioActual
from app.repositories import UsuarioRepository
from app.services.login_service import (
    CorreoNoVerificadoError,
    CredencialesInvalidasError,
    CuentaBloqueadaError,
    LoginService,
)
from app.services.registro_service import RegistroError, RegistroService

router = APIRouter(prefix="/auth", tags=["autenticación"])

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


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
        tiene_letra = any(caracter.isalpha() for caracter in valor)
        tiene_numero = any(caracter.isdigit() for caracter in valor)
        if not (tiene_letra and tiene_numero):
            raise ValueError("La contraseña debe tener al menos una letra y un número")
        return valor


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
def registrar(datos: RegistroRequest, db: SessionDep):
    servicio = RegistroService(UsuarioRepository(db))
    try:
        return servicio.registrar(datos.nombre_usuario, datos.correo, datos.contrasena)
    except RegistroError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error


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
