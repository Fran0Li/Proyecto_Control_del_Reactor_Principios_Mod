"""Funciones del administrador (US-28): estadísticas globales, bloquear cuentas y ver partidas.

Cerrar una partida colgada lo hace la ruta, porque si el motor está corriendo hay que terminarla
ahí para que los observadores guarden el resultado como en un final normal.
"""

from app.models.partida import EstadoPartida
from app.models.usuario import ROL_ADMIN, Usuario
from app.repositories import PartidaRepository, UsuarioRepository
from app.services.partida_service import PartidaNoDisponibleError, PartidaNoEncontradaError

MEJORES_PUNTAJES = 5


class UsuarioNoEncontradoError(Exception):
    pass


class BloqueoNoPermitidoError(Exception):
    pass


class AdminService:
    def __init__(self, usuarios: UsuarioRepository, partidas: PartidaRepository) -> None:
        self.usuarios = usuarios
        self.partidas = partidas

    def estadisticas(self) -> dict:
        mejores = []
        for jugador_id, puntaje, partida_id in self.partidas.mejores_puntajes(MEJORES_PUNTAJES):
            usuario = self.usuarios.obtener_por_id(jugador_id)
            nombre = usuario.nombre_usuario if usuario else f"Jugador {jugador_id}"
            mejores.append({"nombre": nombre, "puntaje": puntaje or 0, "partida_id": partida_id})
        return {
            "usuarios_registrados": self.usuarios.contar(),
            "usuarios_bloqueados": self.usuarios.contar(solo_bloqueados=True),
            "partidas_jugadas": self.partidas.contar_por_estado(EstadoPartida.finalizada),
            "partidas_activas": self.partidas.contar_por_estado(
                EstadoPartida.esperando, EstadoPartida.en_curso
            ),
            "mejores_puntajes": mejores,
        }

    def cambiar_bloqueo(self, admin: Usuario, usuario_id: int, bloquear: bool) -> Usuario:
        usuario = self.usuarios.obtener_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontradoError(f"El usuario {usuario_id} no existe")
        if bloquear and (usuario.id == admin.id or usuario.rol == ROL_ADMIN):
            raise BloqueoNoPermitidoError("No se puede bloquear a un administrador")
        if bloquear and not usuario.bloqueado:
            # las sesiones abiertas dejan de servir (igual que al cambiar la contraseña)
            usuario.version_sesion = (usuario.version_sesion or 0) + 1
        usuario.bloqueado = bloquear
        return self.usuarios.guardar(usuario)

    def partida_activa(self, partida_id: int):
        """La partida que se quiere cerrar, si existe y no terminó todavía."""
        partida = self.partidas.obtener_por_id(partida_id)
        if partida is None:
            raise PartidaNoEncontradaError(f"La partida {partida_id} no existe")
        if partida.estado == EstadoPartida.finalizada:
            raise PartidaNoDisponibleError("La partida ya terminó")
        return partida

    def cerrar_sin_motor(self, partida) -> None:
        """Una partida que quedó abierta en la base (por ejemplo, si se reinició el servidor)."""
        self.partidas.cambiar_estado(partida, EstadoPartida.finalizada)
