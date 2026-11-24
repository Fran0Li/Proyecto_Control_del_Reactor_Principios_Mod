"""Cosas del navegador (pygbag) que no existen en escritorio: abrir páginas y pedir texto."""

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
