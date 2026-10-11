"""Peticiones HTTP al backend que funcionan en escritorio y en el navegador (ADR 0002).

- Escritorio: usa `requests` en un hilo aparte (`asyncio.to_thread`), así no congela la ventana.
- Navegador (pygbag): usa `fetch` de JavaScript. JS guarda la respuesta y Python la recoge sin
  bloquear, igual que el WebSocket del prototipo móvil.

Las pantallas no llaman a esto directamente: usan `src.api_client`.
"""

import asyncio
import itertools
import json
import sys
import time
from dataclasses import dataclass
from typing import Any

EN_NAVEGADOR = sys.platform == "emscripten"
TIMEOUT_S = 5.0


class ErrorDeRed(Exception):
    """No se pudo contactar al servidor (caído, sin red, tiempo agotado)."""


@dataclass(frozen=True)
class Respuesta:
    estado: int
    datos: Any  # JSON ya convertido, o None si el cuerpo no era JSON

    @property
    def ok(self) -> bool:
        return 200 <= self.estado < 300


async def solicitar(
    metodo: str, url: str, cuerpo: dict | None = None, timeout: float = TIMEOUT_S
) -> Respuesta:
    if EN_NAVEGADOR:
        return await _solicitar_navegador(metodo, url, cuerpo, timeout)
    return await _solicitar_escritorio(metodo, url, cuerpo, timeout)


def _a_json(texto: str) -> Any:
    try:
        return json.loads(texto) if texto else None
    except ValueError:
        return None


async def _solicitar_escritorio(
    metodo: str, url: str, cuerpo: dict | None, timeout: float
) -> Respuesta:
    import requests  # solo en escritorio: pygbag no lo trae

    def hacer() -> Respuesta:
        try:
            r = requests.request(metodo, url, json=cuerpo, timeout=timeout)
        except requests.RequestException as error:
            raise ErrorDeRed(str(error)) from error
        return Respuesta(r.status_code, _a_json(r.text))

    return await asyncio.to_thread(hacer)


_ids = itertools.count(1)


async def _solicitar_navegador(
    metodo: str, url: str, cuerpo: dict | None, timeout: float
) -> Respuesta:
    import platform  # en pygbag da acceso a window

    ventana = platform.window
    pid = next(_ids)
    opciones: dict[str, Any] = {"method": metodo}
    if cuerpo is not None:
        opciones["headers"] = {"Content-Type": "application/json"}
        opciones["body"] = json.dumps(cuerpo)

    ventana.eval(
        "(function () {"
        "  window.__cr_http = window.__cr_http || {};"
        f"  fetch({json.dumps(url)}, {json.dumps(opciones)})"
        "    .then(r => r.text().then(t => {"
        f"      window.__cr_http[{pid}] = JSON.stringify({{estado: r.status, texto: t}});"
        "    }))"
        "    .catch(e => {"
        f"      window.__cr_http[{pid}] = JSON.stringify({{error: String(e)}});"
        "    });"
        "})()"
    )

    recoger = (
        "(function () {"
        f"  const v = (window.__cr_http || {{}})[{pid}];"
        f"  if (v === undefined) return '';"
        f"  delete window.__cr_http[{pid}];"
        "  return v;"
        "})()"
    )
    limite = time.monotonic() + timeout
    while True:
        resultado = str(ventana.eval(recoger) or "")
        if resultado:
            break
        if time.monotonic() > limite:
            raise ErrorDeRed("tiempo de espera agotado")
        await asyncio.sleep(0.02)

    datos = json.loads(resultado)
    if "error" in datos:
        raise ErrorDeRed(datos["error"])
    return Respuesta(int(datos["estado"]), _a_json(datos["texto"]))
