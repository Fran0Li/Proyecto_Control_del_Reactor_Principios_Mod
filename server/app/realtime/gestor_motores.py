"""Un motor de partida por partida con jugadores conectados."""

import asyncio

from app.db.session import SessionLocal
from app.realtime.actualizador_ranking import ActualizadorRanking
from app.realtime.cierre_partida import CierrePartida
from app.realtime.connection_manager import ConnectionManager, manager
from app.realtime.escenarios import crear_escenario
from app.realtime.evaluador_logros import EvaluadorLogros, FabricaSesiones
from app.realtime.eventos import PARTIDA_FINALIZADA, EventoPartida
from app.realtime.eventos_especiales import ProgramadorEventos
from app.realtime.motor_partida import EN_CURSO, ESPERANDO, FINALIZADA, MotorPartida
from app.realtime.notificador_websocket import NotificadorWebSocket
from app.realtime.registro_eventos import RegistroEventos
from app.realtime.retos import GestorRetos
from app.repositories.partida_repository import PartidaRepository

# Si todos se van de una partida que no se ha iniciado, se espera este tiempo (por si alguien
# recarga la página o vuelve) y, si sigue vacía, se cierra para que nadie quede trabado en ella.
ESPERA_ANTES_DE_CERRAR_S = 60.0


class GestorMotores:
    def __init__(
        self, canales: ConnectionManager, fabrica_sesiones: FabricaSesiones = SessionLocal
    ) -> None:
        self._canales = canales
        self._fabrica_sesiones = fabrica_sesiones
        self._motores: dict[int, MotorPartida] = {}
        self._resultados_guardados: set[int] = set()  # partidas terminadas ya guardadas
        self.espera_antes_de_cerrar_s = ESPERA_ANTES_DE_CERRAR_S
        self._cierres: dict[int, asyncio.Task] = {}  # partidas vacías por cerrar

    def obtener(self, partida_id: int, escenario: str | None = None) -> MotorPartida:
        """Devuelve el motor de la partida; si no existe, lo crea y lo pone en marcha.
        `escenario` solo se usa al crearlo (US-09); sin escenario queda la arena básica."""
        motor = self._motores.get(partida_id)
        if motor is None:
            eventos = ProgramadorEventos()  # US-16: puntos dobles e invasión
            if escenario is None:
                motor = MotorPartida(partida_id, eventos=eventos)
            else:
                arena, guardianes = crear_escenario(escenario)
                motor = MotorPartida(
                    partida_id,
                    arena=arena,
                    guardianes=guardianes,
                    escenario=escenario,
                    eventos=eventos,
                )
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
        if motor.estado_partida == ESPERANDO:
            self._programar_cierre(partida_id)

    def _programar_cierre(self, partida_id: int) -> None:
        anterior = self._cierres.get(partida_id)
        if anterior is not None and not anterior.done():
            return
        self._cierres[partida_id] = asyncio.get_running_loop().create_task(
            self._cerrar_si_sigue_vacia(partida_id)
        )

    async def _cerrar_si_sigue_vacia(self, partida_id: int) -> None:
        """Cierra en la base una partida sin iniciar que se quedó sin nadie conectado."""
        try:
            await asyncio.sleep(self.espera_antes_de_cerrar_s)
            if self._canales.conectados(partida_id) or partida_id in self._motores:
                return  # alguien volvió
            await asyncio.to_thread(self._cerrar_en_base, partida_id)
        finally:
            self._cierres.pop(partida_id, None)

    def _cerrar_en_base(self, partida_id: int) -> bool:
        with self._fabrica_sesiones() as sesion:
            return PartidaRepository(sesion).cerrar_si_sigue_esperando(partida_id)

    async def al_evento(self, evento: EventoPartida) -> None:
        if evento.tipo == PARTIDA_FINALIZADA:
            self._resultados_guardados.add(evento.partida_id)
            # se hace en otra tarea: el motor no puede detenerse a sí mismo dentro de su tick
            asyncio.get_running_loop().create_task(self.liberar_si_esta_vacio(evento.partida_id))

    def limpiar(self) -> None:
        """Olvida todos los motores (para las pruebas)."""
        self._motores.clear()
        for tarea in self._cierres.values():
            tarea.cancel()
        self._cierres.clear()
        self._resultados_guardados.clear()


gestor_motores = GestorMotores(manager)