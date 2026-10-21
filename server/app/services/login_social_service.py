"""Crear o vincular la cuenta de quien entra con Google (US-04)."""

import re

from app.models.usuario import Usuario
from app.repositories import UsuarioRepository
from app.services.google_oauth import PerfilGoogle


class CorreoGoogleSinVerificarError(Exception):
    pass


class LoginSocialService:
    def __init__(self, usuarios: UsuarioRepository) -> None:
        self.usuarios = usuarios

    def entrar_con_google(self, perfil: PerfilGoogle) -> Usuario:
        if not perfil.correo_verificado:
            raise CorreoGoogleSinVerificarError("Tu cuenta de Google no tiene el correo verificado")

        usuario = self.usuarios.obtener_por_google_id(perfil.google_id)
        if usuario is not None:
            return usuario

        usuario = self.usuarios.obtener_por_correo(perfil.correo)
        if usuario is not None:
            return self._vincular(usuario, perfil)

        nuevo = Usuario(
            nombre_usuario=self._nombre_libre(perfil.correo),
            correo=perfil.correo,
            correo_verificado=True,  # Google ya lo verificó
            google_id=perfil.google_id,
        )
        return self.usuarios.crear(nuevo)

    def _vincular(self, usuario: Usuario, perfil: PerfilGoogle) -> Usuario:
        """Ya había una cuenta con ese correo: se usa la misma en vez de crear otra (RN-01)."""
        if not usuario.correo_verificado:
            # La cuenta la creó alguien que nunca demostró ser dueño del correo; el dueño real
            # es quien entra con Google, así que esa contraseña deja de servir.
            usuario.contrasena_hash = None
            usuario.version_sesion = (usuario.version_sesion or 0) + 1
        usuario.google_id = perfil.google_id
        usuario.correo_verificado = True
        return self.usuarios.guardar(usuario)

    def _nombre_libre(self, correo: str) -> str:
        """Nombre de usuario a partir del correo: luis.serrano@gmail.com -> luisserrano."""
        base = re.sub(r"[^A-Za-z0-9_]", "", correo.split("@")[0])[:26]
        if len(base) < 3:
            base = "jugador"
        nombre = base
        numero = 1
        while self.usuarios.existe_nombre_usuario(nombre):
            numero += 1
            nombre = f"{base}{numero}"
        return nombre
