"""Resultado de una partida terminada, para la ceremonia de victoria (US-18).

Junta lo que guardaron los observadores al terminar (US-17): puestos y puntajes de
`participaciones`, cuántas acciones y penalizaciones tuvo cada jugador según `eventos`, los logros
que se desbloquearon en la partida (US-27) y si alguien hizo su récord personal.
"""

from app.models.partida import EstadoPartida
from app.realtime.eventos import ACCION_REALIZADA, JUGADOR_PENALIZADO, PARTIDA_FINALIZADA
from app.realtime.logros import POR_CLAVE
from app.repositories import (
    EventoRepository,
    LogroRepository,
    PartidaRepository,
    UsuarioRepository,
)
from app.services.partida_service import PartidaNoEncontradaError


class PartidaSinTerminarError(Exception):
    pass


class ResultadoService:
    def __init__(
        self,
        partidas: PartidaRepository,
        usuarios: UsuarioRepository,
        eventos: EventoRepository,
        logros: LogroRepository,
    ) -> None:
        self.partidas = partidas
        self.usuarios = usuarios
        self.eventos = eventos
        self.logros = logros

    def resultado(self, partida_id: int) -> dict:
        partida = self.partidas.obtener_por_id(partida_id)
        if partida is None:
            raise PartidaNoEncontradaError(f"La partida {partida_id} no existe")
        if partida.estado != EstadoPartida.finalizada:
            raise PartidaSinTerminarError("La partida todavía no terminó")

        acciones = self.eventos.contar_por_jugador(partida_id, ACCION_REALIZADA)
        penalizaciones = self.eventos.contar_por_jugador(partida_id, JUGADOR_PENALIZADO)
        logros: dict[int, list[dict]] = {}
        for fila in self.logros.de_partida(partida_id):
            logro = POR_CLAVE.get(fila.logro)
            if logro is not None:
                logros.setdefault(fila.jugador_id, []).append(
                    {"clave": logro.clave, "nombre": logro.nombre}
                )

        jugadores = []
        for participacion in self.partidas.listar_participaciones(partida_id):
            jugador_id = participacion.jugador_id
            usuario = self.usuarios.obtener_por_id(jugador_id)
            puntaje = participacion.puntaje_final or 0
            anterior = self.partidas.mejor_puntaje_antes(jugador_id, partida_id)
            jugadores.append(
                {
                    "jugador_id": jugador_id,
                    "nombre": usuario.nombre_usuario if usuario else f"Jugador {jugador_id}",
                    "puntaje": puntaje,
                    "posicion": participacion.posicion_final,
                    "acciones": acciones.get(jugador_id, 0),
                    "penalizaciones": penalizaciones.get(jugador_id, 0),
                    "logros": logros.get(jugador_id, []),
                    "record_personal": puntaje > 0 and (anterior is None or puntaje > anterior),
                }
            )
        # quien no terminó la partida (sin puesto) va al final
        jugadores.sort(key=lambda j: (j["posicion"] is None, j["posicion"] or 0, j["jugador_id"]))

        fin = self.eventos.ultimo(partida_id, PARTIDA_FINALIZADA)
        datos_fin = fin.datos if fin is not None and fin.datos else {}
        return {
            "partida_id": partida_id,
            "motivo": datos_fin.get("motivo"),
            "duracion_s": datos_fin.get("duracion_s"),
            "ganador_id": datos_fin.get("ganador_id"),
            "jugadores": jugadores,
        }
