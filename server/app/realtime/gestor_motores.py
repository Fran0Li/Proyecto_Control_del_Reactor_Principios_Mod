"""Un motor de partida por partida con jugadores conectados."""

from app.db.session import SessionLocal
from app.realtime.connection_manager import ConnectionManager, manager
from app.realtime.evaluador_logros import EvaluadorLogros, FabricaSesiones
from app.realtime.motor_partida import MotorPartida
from app.realtime.notificador_websocket import NotificadorWebSocket


class GestorMotores:
    def __init__(
        self, canales: ConnectionManager, fabrica_sesiones: FabricaSesiones = SessionLocal
    ) -> None:
        self._canales = canales
        self._fabrica_sesiones = fabrica_sesiones
        self._motores: dict[int, MotorPartida] = {}

    def obtener(self, partida_id: int) -> MotorPartida:
        """Devuelve el motor de la partida; si no existe, lo crea y lo pone en marcha."""
        motor = self._motores.get(partida_id)
        if motor is None:
            motor = MotorPartida(partida_id)
            # Los interesados en la partida se suscriben aquí; el motor no los conoce (ADR 0006)
            motor.suscribir(NotificadorWebSocket(self._canales))
            motor.suscribir(EvaluadorLogros(self._fabrica_sesiones))  # US-27
            self._motores[partida_id] = motor
        motor.iniciar()
        return motor

    def existente(self, partida_id: int) -> MotorPartida | None:
        """El motor de la partida si ya existe; no lo crea."""
        return self._motores.get(partida_id)

    async def liberar_si_esta_vacio(self, partida_id: int) -> None:
        motor = self._motores.get(partida_id)
        if motor is not None and not motor.hay_jugadores:
            await motor.detener()
            del self._motores[partida_id]

    def limpiar(self) -> None:
        """Olvida todos los motores (para las pruebas)."""
        self._motores.clear()


gestor_motores = GestorMotores(manager)