"""Dependencias que comparten varios endpoints."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TokenInvalidoError, leer_token_acceso
from app.db.session import get_session
from app.models.usuario import Usuario
from app.repositories import UsuarioRepository

SessionDep = Annotated[Session, Depends(get_session)]
bearer = HTTPBearer(auto_error=False)


def usuario_actual(
    db: SessionDep,
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Usuario:
    """Devuelve el usuario del token `Authorization: Bearer ...` o responde 401."""
    if credenciales is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tenés que iniciar sesión")
    try:
        usuario_id = leer_token_acceso(credenciales.credentials)
    except TokenInvalidoError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error)) from error

    usuario = UsuarioRepository(db).obtener_por_id(usuario_id)
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "La sesión no es válida o ya venció")
    return usuario


UsuarioActual = Annotated[Usuario, Depends(usuario_actual)]
