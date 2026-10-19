"""Hash de contraseñas (US-01) y token de sesión JWT (US-03)."""

import hashlib
import hmac
import secrets
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings

HORAS_SESION = 12


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, contrasena: str) -> str: ...

    @abstractmethod
    def verificar(self, contrasena: str, hash_guardado: str) -> bool: ...


class ScryptPasswordHasher(PasswordHasher):
    # se guarda como: scrypt$n$r$p$sal$clave
    ALGORITMO = "scrypt"
    MEMORIA_MAXIMA = 64 * 1024 * 1024

    def __init__(self, n: int = 2**14, r: int = 8, p: int = 1, largo_clave: int = 64) -> None:
        self.n = n
        self.r = r
        self.p = p
        self.largo_clave = largo_clave

    def hash(self, contrasena: str) -> str:
        sal = secrets.token_bytes(16)
        clave = self._derivar(contrasena, sal, self.n, self.r, self.p, self.largo_clave)
        return f"{self.ALGORITMO}${self.n}${self.r}${self.p}${sal.hex()}${clave.hex()}"

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        try:
            algoritmo, n, r, p, sal_hex, clave_hex = hash_guardado.split("$")
            if algoritmo != self.ALGORITMO:
                return False
            sal = bytes.fromhex(sal_hex)
            esperada = bytes.fromhex(clave_hex)
            clave = self._derivar(contrasena, sal, int(n), int(r), int(p), len(esperada))
        except ValueError:
            return False
        return hmac.compare_digest(clave, esperada)

    def _derivar(
        self, contrasena: str, sal: bytes, n: int, r: int, p: int, largo: int
    ) -> bytes:
        return hashlib.scrypt(
            contrasena.encode("utf-8"),
            salt=sal,
            n=n,
            r=r,
            p=p,
            maxmem=self.MEMORIA_MAXIMA,
            dklen=largo,
        )


def generar_token() -> str:
    """Token largo para enlaces (verificación de correo)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class TokenInvalidoError(Exception):
    pass


def crear_token_acceso(usuario_id: int, version_sesion: int = 0) -> str:
    # "ver" permite cerrar todas las sesiones de un usuario subiendo su version_sesion (US-05)
    expira = datetime.now(UTC) + timedelta(hours=HORAS_SESION)
    datos = {"sub": str(usuario_id), "ver": version_sesion, "exp": expira}
    return jwt.encode(datos, settings.jwt_secret, "HS256")


def leer_token_acceso(token: str) -> tuple[int, int]:
    """Devuelve (usuario_id, version_sesion)."""
    try:
        datos = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return int(datos["sub"]), int(datos["ver"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as error:
        raise TokenInvalidoError("La sesión no es válida o ya venció") from error
