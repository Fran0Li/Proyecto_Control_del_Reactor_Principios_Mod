# Prototipo: cliente móvil con pygbag

Prueba técnica para decidir cómo cumplir con la versión móvil. **No es el cliente del juego**:
sirve para comprobar que el mismo código pygame corre en la PC y en el navegador del celular,
y que ambos hablan con el servidor usando el contrato de `docs/contrato-api-hardware.md`.

| Archivo | Qué hace |
| --- | --- |
| `main.py` | Cliente: ciclo `async`, dibuja a los jugadores y muestra conexión y latencia |
| `red.py` | Conexión WebSocket con una versión para PC y otra para navegador |
| `entrada.py` | Teclado y botones táctiles en pantalla, con la misma interfaz |
| `servidor_eco.py` | Servidor de prueba: mueve a los jugadores en ciclos de 50 ms y difunde el estado |

## Cómo probarlo

Todo desde esta carpeta (`prototipos/cliente-movil`), en la PC.

1. Instalar dependencias (una vez):
   ```
   pip install -r requirements.txt
   ```
2. Levantar el servidor de prueba (terminal 1):
   ```
   uvicorn servidor_eco:app --host 0.0.0.0 --port 8002
   ```
3. Cliente de escritorio (terminal 2):
   ```
   python main.py
   ```
4. Cliente web con pygbag (terminal 3):
   ```
   pygbag --bind 0.0.0.0 --port 8001 .
   ```
   - En la PC: abrir `http://localhost:8001`.
   - En el celular, **conectado al mismo WiFi**: abrir `http://<IP-de-la-PC>:8001`.
     La IP se ve con `ipconfig` (IPv4 del adaptador WiFi).
   - Tocar la pantalla cuando diga "Ready to start".

Si Windows pregunta por el firewall al iniciar Python, hay que permitir **redes privadas**.
Si el celular no carga, revisar que la red WiFi esté marcada como privada en Windows.

## Qué validar

| # | Prueba | Resultado |
| --- | --- | --- |
| 1 | `pygbag` compila y la página carga en la PC | |
| 2 | La página carga en el celular | |
| 3 | En el navegador dice "Conexión: abierta" | |
| 4 | Los botones táctiles mueven al jugador en el celular | |
| 5 | Desde PC (teclado) y celular (táctil) a la vez, cada uno ve moverse al otro | |
| 6 | Mantener presionado y soltar: el jugador se detiene al soltar | |
| 7 | Latencia mostrada en el celular menor a 500 ms (RNF-02) | |
| 8 | Fluidez aceptable en el celular (sin tirones fuertes) | |

Validado aquí, sin el celular:
- Cliente de escritorio + servidor: dos clientes a la vez, teclado y táctil, el jugador se detiene
  al soltar, entrada inválida responde `error`, latencia local de unos 20 ms.
- `red.ConexionNavegador` ejecutado contra el motor JavaScript real de Chromium: conecta, envía
  y recibe con el formato del contrato.

Falta validarlo con el runtime de pygbag y en un celular real (pruebas 1 a 8).

## Reglas para el cliente real si la prueba sale bien

1. El ciclo principal es `async def main()` y llama a `await asyncio.sleep(0)` en cada frame.
2. Nada bloqueante en el cliente: ni `requests`, ni `time.sleep`, ni sockets directos. La red va
   detrás de una interfaz con implementación para escritorio y para navegador (`red.py`).
3. Las entradas usan la interfaz de "fuente de entrada" (`entrada.py`): teclado, táctil y Arduino.
4. Imports que solo existen en escritorio (`websockets`, `pyserial`) se hacen dentro de la clase
   de escritorio, para que pygbag no los busque.
5. pygbag usa **pygame-ce**. Conviene usar `pygame-ce` también en escritorio para tener la misma
   versión en las dos plataformas (el código de pygame es compatible).
6. Si la página se sirve por HTTPS (por ejemplo, en la nube), el WebSocket tiene que ser `wss://`.
