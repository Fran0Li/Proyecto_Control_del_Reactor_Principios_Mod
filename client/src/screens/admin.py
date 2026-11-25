"""Pantalla de administración (US-28): estadísticas globales, bloquear cuentas y cerrar partidas.

Solo se llega desde el lobby con una cuenta de administrador; igual el servidor revisa el rol en
cada petición.
"""

import pygame

from src import sesion
from src.api_client import (
    ApiError,
    admin_bloquear,
    admin_cerrar_partida,
    admin_estadisticas,
    admin_partidas,
    admin_usuarios,
)
from src.screens.componentes import Boton, boton_secundario
from src.screens.formulario import PantallaFormulario

COLOR_CAJA = (24, 32, 56)
COLOR_TEXTO = (230, 230, 240)
COLOR_SUAVE = (150, 160, 190)
COLOR_BLOQUEADO = (240, 100, 100)
MAX_FILAS = 7
ALTO_FILA = 40
Y_LISTAS = 255
CAJAS = (
    ("usuarios_registrados", "Usuarios"),
    ("usuarios_bloqueados", "Bloqueados"),
    ("partidas_jugadas", "Jugadas"),
    ("partidas_activas", "Activas"),
)


def boton_rojo(rect: pygame.Rect, texto: str) -> Boton:
    return Boton(rect, texto, color=(150, 50, 50), color_hover=(190, 70, 70))


class AdminScreen(PantallaFormulario):
    titulo = "ADMINISTRACIÓN"
    y_titulo = 45
    y_mensaje = 600

    def __init__(self, width: int) -> None:
        super().__init__(width)
        self.ancho = width
        self.boton_volver = boton_secundario(pygame.Rect(20, 20, 120, 40), "Volver")
        self.estadisticas: dict | None = None
        self.usuarios: list[dict] = []
        self.partidas: list[dict] = []
        self.botones_usuarios: list[tuple[Boton, dict]] = []
        self.botones_partidas: list[tuple[Boton, dict]] = []

    def al_mostrar(self) -> None:
        self.estadisticas = None
        self.mostrar("Cargando...")
        self.lanzar(self._cargar)

    # peticiones

    async def _cargar(self) -> None:
        token = sesion.token()
        try:
            self.estadisticas = await admin_estadisticas(token)
            self.usuarios = await admin_usuarios(token)
            self.partidas = await admin_partidas(token)
        except ApiError as error:
            self.mostrar(str(error), es_error=True)
            return
        self._crear_botones()
        self.mostrar("")

    async def _cambiar_bloqueo(self, usuario: dict) -> None:
        bloquear = not usuario["bloqueado"]
        try:
            await admin_bloquear(sesion.token(), usuario["id"], bloquear)
        except ApiError as error:
            self.mostrar(str(error), es_error=True)
            return
        await self._cargar()
        accion = "bloqueado" if bloquear else "desbloqueado"
        self.mostrar(f"{usuario['nombre_usuario']} quedó {accion}")

    async def _cerrar(self, partida: dict) -> None:
        try:
            await admin_cerrar_partida(sesion.token(), partida["id"])
        except ApiError as error:
            self.mostrar(str(error), es_error=True)
            return
        await self._cargar()
        self.mostrar(f"Partida #{partida['id']} cerrada")

    # eventos

    def handle_event(self, event: pygame.event.Event) -> None:
        escape = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        if escape or self.boton_volver.fue_presionado(event):
            self.siguiente_pantalla = "lobby"
            return
        for boton, usuario in self.botones_usuarios:
            if boton.fue_presionado(event):
                self.lanzar(lambda usuario=usuario: self._cambiar_bloqueo(usuario))
                return
        for boton, partida in self.botones_partidas:
            if boton.fue_presionado(event):
                self.lanzar(lambda partida=partida: self._cerrar(partida))
                return

    # dibujo

    def _crear_botones(self) -> None:
        self.botones_usuarios = []
        for i, usuario in enumerate(self.usuarios[:MAX_FILAS]):
            if usuario["rol"] == "administrador":
                continue  # a un admin no se le bloquea
            rect = pygame.Rect(self.centro_x - 170, Y_LISTAS + i * ALTO_FILA + 3, 156, 32)
            if usuario["bloqueado"]:
                boton = boton_secundario(rect, "Desbloquear")
            else:
                boton = boton_rojo(rect, "Bloquear")
            self.botones_usuarios.append((boton, usuario))
        self.botones_partidas = [
            (
                boton_rojo(
                    pygame.Rect(self.ancho - 130, Y_LISTAS + i * ALTO_FILA + 4, 100, 32), "Cerrar"
                ),
                partida,
            )
            for i, partida in enumerate(self.partidas[:MAX_FILAS])
        ]

    def draw(self, screen: pygame.Surface) -> None:
        self.dibujar_base(screen)
        self.boton_volver.draw(screen)
        if self.estadisticas is None:
            return
        self._dibujar_cajas(screen)
        self._dibujar_mejores(screen)
        self._dibujar_usuarios(screen)
        self._dibujar_partidas(screen)

    def _texto(self, screen, texto, color, x, y, fuente=None) -> None:
        imagen = (fuente or self.fuente_texto).render(str(texto), True, color)
        screen.blit(imagen, imagen.get_rect(midleft=(x, y)))

    def _dibujar_cajas(self, screen: pygame.Surface) -> None:
        ancho = 140
        x = 30
        for clave, etiqueta in CAJAS:
            rect = pygame.Rect(x, 85, ancho - 10, 70)
            pygame.draw.rect(screen, COLOR_CAJA, rect, border_radius=10)
            valor = self.fuente_titulo.render(str(self.estadisticas[clave]), True, COLOR_TEXTO)
            screen.blit(valor, valor.get_rect(center=(rect.centerx, rect.y + 26)))
            nombre = self.fuente_texto.render(etiqueta, True, COLOR_SUAVE)
            screen.blit(nombre, nombre.get_rect(center=(rect.centerx, rect.y + 56)))
            x += ancho

    def _dibujar_mejores(self, screen: pygame.Surface) -> None:
        x = 610
        self._texto(screen, "Mejores puntajes", COLOR_SUAVE, x, 95)
        for i, mejor in enumerate(self.estadisticas["mejores_puntajes"][:4]):
            partida = f"partida #{mejor['partida_id']}"
            linea = f"{i + 1}. {mejor['nombre']}  {mejor['puntaje']} ({partida})"
            self._texto(screen, linea, COLOR_TEXTO, x, 120 + i * 22)

    def _dibujar_usuarios(self, screen: pygame.Surface) -> None:
        self._texto(screen, "Usuarios", COLOR_SUAVE, 30, Y_LISTAS - 20)
        for i, usuario in enumerate(self.usuarios[:MAX_FILAS]):
            y = Y_LISTAS + i * ALTO_FILA
            rect = pygame.Rect(30, y, self.centro_x - 40, ALTO_FILA - 4)
            pygame.draw.rect(screen, COLOR_CAJA, rect, border_radius=8)
            color = COLOR_BLOQUEADO if usuario["bloqueado"] else COLOR_TEXTO
            nombre = usuario["nombre_usuario"][:16]
            if usuario["rol"] == "administrador":
                nombre += " (admin)"
            self._texto(screen, nombre, color, 42, rect.centery)
        for boton, _ in self.botones_usuarios:
            boton.draw(screen)
        if len(self.usuarios) > MAX_FILAS:
            resto = f"... y {len(self.usuarios) - MAX_FILAS} más"
            self._texto(screen, resto, COLOR_SUAVE, 42, Y_LISTAS + MAX_FILAS * ALTO_FILA + 6)

    def _dibujar_partidas(self, screen: pygame.Surface) -> None:
        x = self.centro_x + 20
        self._texto(screen, "Partidas activas", COLOR_SUAVE, x, Y_LISTAS - 20)
        if not self.partidas:
            self._texto(screen, "No hay partidas abiertas", COLOR_SUAVE, x, Y_LISTAS + 18)
        for i, partida in enumerate(self.partidas[:MAX_FILAS]):
            y = Y_LISTAS + i * ALTO_FILA
            rect = pygame.Rect(x, y, self.ancho - x - 20, ALTO_FILA - 4)
            pygame.draw.rect(screen, COLOR_CAJA, rect, border_radius=8)
            estado = str(partida["estado"]).replace("_", " ")
            jugadores = partida["jugadores"]
            plural = "jugador" if jugadores == 1 else "jugadores"
            linea = f"#{partida['id']}  {estado}  {jugadores} {plural}"
            self._texto(screen, linea, COLOR_TEXTO, x + 12, rect.centery)
        for boton, _ in self.botones_partidas:
            boton.draw(screen)
