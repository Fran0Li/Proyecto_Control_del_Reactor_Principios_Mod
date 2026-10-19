"""Recuperación de contraseña (US-05).

Se manda un código corto al correo; con ese código se elige una contraseña nueva y se cierran
todas las sesiones abiertas de la cuenta.
"""

from datetime import timedelta

from app.core.security import PasswordHasher, ScryptPasswordHasher, generar_codigo
from app.models.usuario import Usuario
from app.repositories import UsuarioRepository
from app.services.correo import EnviadorCorreo
from app.services.tokens_correo import TokenNoValidoError, TokensDeCorreo

TIPO = "recuperacion"
MINUTOS_VALIDEZ = 15


class RecuperacionService:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        tokens: TokensDeCorreo,
        enviador: EnviadorCorreo,
        hasher: PasswordHasher | None = None,
    ) -> None:
        self.usuarios = usuarios
        self.tokens = tokens
        self.enviador = enviador
        self.hasher = hasher or ScryptPasswordHasher()

    def solicitar(self, correo: str) -> None:
        # misma respuesta exista o no la cuenta, para no revelar qué correos están registrados
        usuario = self.usuarios.obtener_por_correo(correo.strip().lower())
        if usuario is None:
            return

        codigo = generar_codigo()
        self.tokens.guardar(usuario.id, TIPO, codigo, timedelta(minutes=MINUTOS_VALIDEZ))
        self.enviador.enviar(
            usuario.correo,
            "Código para cambiar tu contraseña",
            f"Hola {usuario.nombre_usuario}:\n\n"
            f"Tu código es: {codigo}\n\n"
            "Escribilo en el juego para elegir una contraseña nueva. "
            f"Vence en {MINUTOS_VALIDEZ} minutos.\n"
            "Si no pediste cambiar la contraseña, ignorá este correo.",
        )

    def restablecer(self, correo: str, codigo: str, contrasena_nueva: str) -> Usuario:
        usuario = self.usuarios.obtener_por_correo(correo.strip().lower())
        if usuario is None:
            raise TokenNoValidoError()
        self.tokens.usar(codigo.upper(), TIPO, usuario.id)

        usuario.contrasena_hash = self.hasher.hash(contrasena_nueva)
        usuario.version_sesion = (usuario.version_sesion or 0) + 1  # cierra las sesiones abiertas
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.correo_verificado = True  # le llegó el código, así que el correo es suyo
        return self.usuarios.guardar(usuario)
