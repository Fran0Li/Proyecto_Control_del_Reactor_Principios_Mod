"""Ranking global (US-19) e historial del jugador (US-20).

El ranking sale de `ranking_global`, que el ActualizadorRanking suma al terminar cada partida
(US-17), así que se actualiza solo. El historial es siempre el del jugador autenticado.
"""

from app.repositories import LogroRepository, PartidaRepository, RankingRepository

TOP = 10
PARTIDAS_EN_HISTORIAL = 20


class RankingService:
    def __init__(self, ranking: RankingRepository) -> None:
        self.ranking = ranking

    def ranking_global(self, jugador_id: int) -> dict:
        top = []
        for fila, nombre in self.ranking.top(TOP):
            top.append(self._fila(fila, nombre, self.ranking.posicion(fila)))
        propia = self.ranking.de_jugador(jugador_id)
        yo = None
        if propia is not None:
            yo = self._fila(propia, None, self.ranking.posicion(propia))
        return {"top": top, "yo": yo}

    @staticmethod
    def _fila(fila, nombre: str | None, posicion: int) -> dict:
        return {
            "posicion": posicion,
            "jugador_id": fila.jugador_id,
            "nombre": nombre,
            "puntos_totales": fila.puntos_totales or 0,
            "victorias": fila.victorias or 0,
        }


class HistorialService:
    def __init__(
        self, partidas: PartidaRepository, ranking: RankingRepository, logros: LogroRepository
    ) -> None:
        self.partidas = partidas
        self.ranking = ranking
        self.logros = logros

    def historial(self, jugador_id: int) -> dict:
        jugadas, mejor = self.partidas.resumen_de(jugador_id)
        acumulado = self.ranking.de_jugador(jugador_id)
        partidas = [
            {
                "partida_id": partida.id,
                "fecha": partida.fecha_fin,
                "escenario": partida.escenario,
                "puntaje": participacion.puntaje_final or 0,
                "posicion": participacion.posicion_final,
                "jugadores": self.partidas.contar_participantes(partida.id),
                "gano": participacion.posicion_final == 1,
            }
            for partida, participacion in self.partidas.historial(jugador_id, PARTIDAS_EN_HISTORIAL)
        ]
        return {
            "resumen": {
                "partidas_jugadas": jugadas,
                "victorias": (acumulado.victorias or 0) if acumulado else 0,
                "puntos_totales": (acumulado.puntos_totales or 0) if acumulado else 0,
                "mejor_puntaje": mejor,
                "logros": len(self.logros.claves_obtenidas(jugador_id)),
            },
            "partidas": partidas,
        }
