from fastapi.responses import HTMLResponse


def pagina_simple(titulo: str, texto: str, estado: int = 200) -> HTMLResponse:
    """Página corta para lo que el jugador abre en el navegador (enlaces del correo, Google)."""
    html = (
        '<!doctype html><html lang="es"><meta charset="utf-8">'
        "<title>Control del Reactor</title>"
        '<body style="font-family:sans-serif;background:#0c1020;color:#e6e6f0;'
        'text-align:center;padding-top:15vh">'
        f'<h1 style="color:#50c8ff">{titulo}</h1><p>{texto}</p></body></html>'
    )
    return HTMLResponse(html, status_code=estado)
