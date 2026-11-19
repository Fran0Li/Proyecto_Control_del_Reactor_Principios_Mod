"""Abrir una página en el navegador, en escritorio y en pygbag."""

import sys


def abrir_url(url: str) -> None:
    if sys.platform == "emscripten":
        import platform  # en pygbag da acceso a window

        platform.window.open(url, "_blank")
    else:
        import webbrowser

        webbrowser.open(url)


def es_pantalla_tactil() -> bool:
    """True en el navegador de un celular o tablet (pantalla táctil como puntero principal)."""
    if sys.platform != "emscripten":
        return False
    import platform

    try:
        return bool(platform.window.matchMedia("(pointer: coarse)").matches)
    except Exception:  # navegador viejo sin matchMedia: se sigue como en escritorio
        return False


def pedir_texto(etiqueta: str, actual: str) -> str | None:
    """Abre el cuadro de texto del navegador, que en el celular sí muestra el teclado.

    pygame en el navegador no puede abrir el teclado del celular, así que los campos de texto lo
    piden así. Devuelve None si el jugador cancela.
    """
    import platform

    respuesta = platform.window.prompt(etiqueta, actual)
    return None if respuesta is None else str(respuesta)
