# Cliente del juego (pygame)

El mismo código corre en la PC y en el navegador del celular (pygbag). Las reglas para que siga
funcionando en los dos están en `docs/adr/0002-cliente-movil-pygbag.md`.

## Correr en la PC

En Windows, lo más fácil es el script: instala lo que falte, pone el puerto del control y avisa si
el backend no responde.

```
.\jugar.ps1                 # control en COM5, backend local
.\jugar.ps1 -Puerto COM3    # si Windows le asignó otro puerto a la placa
.\jugar.ps1 -Simulador      # sin la placa, con hardware/simulator
.\jugar.ps1 -SinControl     # solo teclado
.\jugar.ps1 -Nube           # contra la VM de Azure
```

Si PowerShell no deja correr el script, en esa terminal:
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`.

A mano, o en Linux y Mac:

```
pip uninstall -y pygame          # solo la primera vez, si tenías pygame normal instalado
pip install -r requirements.txt
python main.py
```

El backend tiene que estar corriendo (`docker compose up` en la raíz). Para otro servidor:
`SERVER_URL=http://otra-ip:8000`.

Con el control físico, el **Monitor Serie del Arduino IDE tiene que estar cerrado**: ocupa el
puerto COM y el cliente no lo puede abrir.

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

En la nube la página se sirve con https y el cliente usa `https://<dominio>/api` (ver
`docs/despliegue.md`). Para jugar desde la PC contra la nube: `SERVER_URL=https://<dominio>/api`.

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

## Probar el control sin la ventana del juego

`probar_control.py` hace de cliente sin ventana para las pruebas de aceptación del control
(CP-274 latencia, CP-285 desconexión y CP-301 extracción, en `docs/pruebas/sprint-3/`). Inicia
sesión, crea una partida, lee el Arduino con el mismo `EntradaSerial` del juego y muestra la
latencia de cada botón, la distancia al reactor, el puntaje y cuándo se conecta o desconecta el
control. Con Ctrl+C imprime el resumen y guarda las mediciones en `latencia_<fecha>.csv`.

```
python probar_control.py                   # COM5, backend local
python probar_control.py --puerto COM3
python probar_control.py --partida 7       # si la cuenta ya está en la partida 7
```

Mide desde que la PC lee `BTN ... PRESS` hasta que el servidor devuelve la posición nueva. No
cuenta el antirrebote del firmware (20 ms), el USB ni el dibujo del cuadro; el resumen les suma
40 ms de margen.

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

## Escribir desde el celular

El canvas de pygame no abre el teclado del teléfono. En pantallas táctiles, tocar un campo de texto
abre el cuadro de texto del navegador (`window.prompt`), que sí lo abre; lo escrito pasa al campo
(`src/navegador.py`, `pedir_texto`). En la compu, también en el navegador, se escribe como siempre.
Limitación: en ese cuadro la contraseña se ve mientras se escribe; en el juego queda con asteriscos.

## Sonidos (US-29)

En la arena suena la música de la partida en bucle (`assets/audio/musica_partida.ogg`) y efectos
generados en código (`src/sonidos.py`): extraer del reactor, recoger una bolita de energía, el
golpe de un guardián (a cualquier jugador) y el inicio de un evento especial. `DetectorSonidos`
los decide comparando cada estado del servidor con el anterior, sin cambios en el servidor. La
tecla **M** silencia todo. Sin audio disponible el juego sigue igual. Detalles en
`assets/audio/README.md`.

## Toques: Android e iPhone

Los botones y campos (`Boton`, `CampoTexto`) aceptan el dedo (`FINGERDOWN`) y el clic de mouse.
Safari del iPhone solo manda el dedo; Android manda el dedo y después un clic inventado a partir de
él, así que una vez que se vio un dedo se ignoran los clics para no presionar dos veces
(`componentes.punto_presionado`).

## Pantalla completa en el celular

En Chrome de Android, el primer toque pone el juego en pantalla completa y horizontal
(`navegador.al_tocar`, desde `main.py`); si el jugador sale, el siguiente toque la vuelve a pedir.
Safari del iPhone no permite pantalla completa en páginas, así que ahí se ve como antes.

Antes de que el creador inicie la partida, la arena es de práctica (no cuenta) y muestra el botón
"Volver al lobby", porque en el celular no hay Esc. Si la partida empieza mientras alguien está en
práctica, el servidor lo manda a su punto de inicio con 0 puntos y el reloj arranca.

## Pruebas

```
pip install pytest
pytest
```
