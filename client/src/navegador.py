"""Cosas del navegador (pygbag) que no existen en escritorio: abrir páginas, pedir texto y
pantalla completa en el celular."""

import sys

EN_NAVEGADOR = sys.platform == "emscripten"


def abrir_url(url: str) -> None:
    if EN_NAVEGADOR:
        import platform  # en pygbag da acceso a window

        platform.window.open(url, "_blank")
    else:
        import webbrowser

        webbrowser.open(url)


def es_pantalla_tactil() -> bool:
    """True en el navegador de un celular o tablet (el dedo es el puntero principal)."""
    if not EN_NAVEGADOR:
        return False
    import platform

    try:
        return bool(platform.window.matchMedia("(pointer: coarse)").matches)
    except Exception:  # navegador viejo sin matchMedia: se asume que no es táctil
        return False


def pedir_texto(etiqueta: str, actual: str = "") -> str | None:
    """Abre el cuadro de texto del navegador, que en el celular sí saca el teclado del teléfono.

    Devuelve lo escrito, o None si se canceló o no se está en un celular. El canvas de pygame no
    puede abrir el teclado del teléfono, por eso los campos de texto lo usan en pantallas táctiles.
    """
    if not es_pantalla_tactil():
        return None
    import platform

    valor = platform.window.prompt(etiqueta, actual)
    if valor is None or str(valor) in ("null", "undefined"):
        return None
    return str(valor)


# Pantalla completa y horizontal. El navegador solo la permite justo después de un toque del
# jugador, y la orientación solo se puede fijar ya en pantalla completa: por eso va encadenado.
# Funciona en Chrome de Android; Safari del iPhone no tiene pantalla completa para páginas.
JS_PANTALLA_COMPLETA = """(function () {
  var d = document, e = d.documentElement;
  if (d.fullscreenElement || !e.requestFullscreen) return;
  e.requestFullscreen({navigationUI: "hide"}).then(function () {
    if (screen.orientation && screen.orientation.lock) {
      screen.orientation.lock("landscape").catch(function () {});
    }
  }).catch(function () {});
})();"""


def pantalla_completa() -> bool:
    """Pide pantalla completa en el celular. True si se pidió (en la compu no hace nada)."""
    if not es_pantalla_tactil():
        return False
    import platform

    try:
        platform.window.eval(JS_PANTALLA_COMPLETA)
    except Exception:  # si el navegador no deja, el juego sigue igual que antes
        return False
    return True


def al_tocar(evento) -> None:
    """La llama el ciclo principal con cada evento: un toque en el celular pide pantalla completa
    (si el jugador salió de ella, el siguiente toque la vuelve a pedir)."""
    import pygame

    if evento.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
        pantalla_completa()
