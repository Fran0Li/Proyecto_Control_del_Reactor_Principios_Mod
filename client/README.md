# Cliente del juego (pygame)

El mismo código corre en la PC y en el navegador del celular (pygbag). Las reglas para que siga
funcionando en los dos están en `docs/adr/0002-cliente-movil-pygbag.md`.

## Correr en la PC

```
pip uninstall -y pygame          # solo la primera vez, si tenías pygame normal instalado
pip install -r requirements.txt
python main.py
```

El backend tiene que estar corriendo (`docker compose up` en la raíz). Para otro servidor:
`SERVER_URL=http://otra-ip:8000`.

## Correr en el navegador o en el celular

1. Backend corriendo con `docker compose up`.
2. Ver la IP de la PC con `ipconfig` (por ejemplo `192.168.1.50`).
3. Desde esta carpeta:
   ```
   pip install pygbag
   pygbag --bind 192.168.1.50 --port 8001 .
   ```
4. Abrir `http://192.168.1.50:8001` en la PC o en el celular (mismo WiFi).

En el navegador el cliente llama al backend en la misma IP, puerto 8000. Si Windows pregunta por el
firewall, permitir redes privadas.

## Controles en la partida

| Plataforma | Fuentes | `origen` en el mensaje |
| --- | --- | --- |
| PC | Teclado: flechas o WASD y espacio | `teclado` |
| PC con control | Teclado y Arduino o simulador, con `CONTROL_PUERTO` | `hardware` o `simulador` |
| Navegador o celular | Teclado y botones táctiles en pantalla | `teclado` o `tactil` |

```
CONTROL_PUERTO=COM3 python main.py                       # Arduino por USB
CONTROL_PUERTO=socket://localhost:7777 python main.py    # simulador (hardware/simulator)
```

Todas las fuentes implementan `FuenteEntrada` (`src/entrada/`) y `ControlesJugador` envía cada
cambio al canal de la partida con el mensaje `entrada` del contrato de hardware. La pantalla de
juego solo hace esto:

```python
controles = ControlesJugador(crear_fuentes(ancho, alto, CONTROL_PUERTO), canal.enviar)
controles.procesar(evento)   # por cada evento de pygame
controles.actualizar()       # una vez por cuadro
controles.dibujar(pantalla)  # botones táctiles, si hay
controles.cerrar()           # al salir de la partida
```

## Reglas al programar el cliente (ADR 0002)

- **Nada bloqueante.** Nada de `requests`, `time.sleep` ni sockets en las pantallas. Para hablar
  con el servidor se usa `src/api_client.py`, que es `async`.
- **Llamadas al servidor desde una pantalla:** se lanzan como tarea para no congelar la ventana.
  ```python
  def handle_event(self, event):
      if self.boton.fue_presionado(event):
          self._tarea = asyncio.create_task(self._crear())

  async def _crear(self):
      try:
          datos = await crear_partida(JUGADOR_ID)
      except ApiError as error:
          ...
  ```
- **Endpoints nuevos:** agregar una función `async` en `src/api_client.py` usando `_enviar(...)`.
- **Entradas** (teclado, táctil, Arduino): con la interfaz de `src/entrada/`.
- **Librerías solo de escritorio** (`requests`, `pyserial`): importarlas dentro de la función que las
  usa, como en `src/red/http.py`.

## Pendiente para el Sprint 3

- En el celular los campos de texto no abren el teclado del teléfono: hay que agregar un teclado en
  pantalla o un campo HTML para el login y el registro desde el móvil.

## Pruebas

```
pip install pytest
pytest
```
