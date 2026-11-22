"""Un motor de partida por partida con jugadores conectados."""

import asyncio

from app.db.session import SessionLocal
from app.realtime.actualizador_ranking import ActualizadorRanking
from app.realtime.cierre_partida import CierrePartida
from app.realtime.connection_manager import ConnectionManager, manager
from app.realtime.evaluador_logros import EvaluadorLogros, FabricaSesiones
from app.realtime.eventos import PARTIDA_FINALIZADA, EventoPartida
from app.realtime.motor_partida import EN_CURSO, FINALIZADA, MotorPartida
from app.realtime.notificador_websocket import NotificadorWebSocket
from app.realtime.registro_eventos import RegistroEventos
from app.realtime.retos import GestorRetos


class GestorMotores:
    def __init__(
        self, canales: ConnectionManager, fabrica_sesiones: FabricaSesiones = SessionLocal
    ) -> None:
        self._canales = canales
        self._fabrica_sesiones = fabrica_sesiones
        self._motores: dict[int, MotorPartida] = {}
        self._resultados_guardados: set[int] = set()  # partidas terminadas ya guardadas

    def obtener(self, partida_id: int) -> MotorPartida:
        """Devuelve el motor de la partida; si no existe, lo crea y lo pone en marcha."""
        motor = self._motores.get(partida_id)
        if motor is None:
            motor = MotorPartida(partida_id)
            # Los interesados en la partida se suscriben aquí; el motor no los conoce (ADR 0006)
            motor.suscribir(NotificadorWebSocket(self._canales))
            motor.suscribir(EvaluadorLogros(self._fabrica_sesiones))  # US-27
            motor.suscribir(GestorRetos(motor))  # US-27: retos con puntos extra en la partida
            # US-17: guardar el resultado, los eventos y el ranking al terminar
            motor.suscribir(CierrePartida(self._fabrica_sesiones))
            motor.suscribir(RegistroEventos(self._fabrica_sesiones))
            motor.suscribir(ActualizadorRanking(self._fabrica_sesiones))
            # el último: cuando le llega el fin, los anteriores ya guardaron el resultado
            motor.suscribir(self)
            self._motores[partida_id] = motor
        motor.iniciar()
        return motor

    def existente(self, partida_id: int) -> MotorPartida | None:
        """El motor de la partida si ya existe; no lo crea."""
        return self._motores.get(partida_id)

    async def liberar_si_esta_vacio(self, partida_id: int) -> None:
        """Detiene el motor si ya no hay nadie conectado. Una partida en curso sigue corriendo
        hasta el final aunque todos se vayan, para que se guarde su resultado."""
        motor = self._motores.get(partida_id)
        if motor is None or motor.hay_jugadores or motor.estado_partida == EN_CURSO:
            return
        if motor.estado_partida == FINALIZADA and partida_id not in self._resultados_guardados:
            return  # todavía se está guardando el resultado: lo suelta al_evento al terminar
        if self._motores.get(partida_id) is motor:
            del self._motores[partida_id]
        await motor.detener()

    async def al_evento(self, evento: EventoPartida) -> None:
        if evento.tipo == PARTIDA_FINALIZADA:
            self._resultados_guardados.add(evento.partida_id)
            # se hace en otra tarea: el motor no puede detenerse a sí mismo dentro de su tick
            asyncio.get_running_loop().create_task(self.liberar_si_esta_vacio(evento.partida_id))

    def limpiar(self) -> None:
        """Olvida todos los motores (para las pruebas)."""
        self._motores.clear()
        self._resultados_guardados.clear()


gestor_motores = GestorMotores(manager)