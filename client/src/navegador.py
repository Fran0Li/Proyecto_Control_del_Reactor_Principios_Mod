"""Abrir una página en el navegador, en escritorio y en pygbag."""

import sys


def abrir_url(url: str) -> None:
    if sys.platform == "emscripten":
        import platform  # en pygbag da acceso a window

        platform.window.open(url, "_blank")
    else:
        import webbrowser

        webbrowser.open(url)
