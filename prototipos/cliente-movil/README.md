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
4. Cliente web con pygbag (terminal 3). Primero ver la IP de la PC con `ipconfig`
   (Dirección IPv4 del adaptador WiFi, por ejemplo `192.168.1.50`) y usarla en `--bind`:
   ```
   pygbag --bind 192.168.1.50 --port 8001 .
   ```
   > No usar `--bind 0.0.0.0`: pygbag usa esa dirección para que la página descargue su motor y
   > el navegador la rechaza (`ERR_ADDRESS_INVALID`).
   - En la PC y en el celular (**conectado al mismo WiFi**) abrir `http://192.168.1.50:8001`.
   - La primera carga tarda porque descarga el motor de Python para el navegador.
   - Tocar la pantalla cuando diga "Ready to start".

Si Windows pregunta por el firewall al iniciar Python, hay que permitir **redes privadas**.
Si el celular no carga, revisar que la red WiFi esté marcada como privada en Windows.

## Resultados (09/10/2026)

Probado en Chrome de la PC y Chrome de un celular Android, en la misma red WiFi.

| # | Prueba | Resultado |
| --- | --- | --- |
| 1 | `pygbag` compila y la página carga en la PC | ✅ |
| 2 | La página carga en el celular | ✅ |
| 3 | En el navegador dice "Conexión: abierta" | ✅ |
| 4 | Los botones táctiles mueven al jugador en el celular | ✅ |
| 5 | Desde PC (teclado) y celular (táctil) a la vez, cada uno ve moverse al otro | ✅ 3 jugadores a la vez |
| 6 | Mantener presionado y soltar: el jugador se detiene al soltar | ✅ tras la corrección de abajo |
| 7 | Latencia menor a 500 ms (RNF-02) | ✅ 16 ms navegador de PC, 33 ms celular |
| 8 | Fluidez aceptable en el celular | ✅ |

**Problema encontrado y corregido:** en el celular un botón podía quedarse presionado porque el
navegador a veces cancela el toque y no llega el evento de soltar. `Tactil.revisar()` compara en
cada frame los botones presionados con los dedos que siguen en pantalla y suelta los que sobran.
La línea "Eventos táctiles" de la parte de abajo de la pantalla sirve para diagnosticar.

Además, sin celular: el cliente de escritorio y `red.ConexionNavegador` (contra el motor JavaScript
de Chromium) se probaron con dos clientes simultáneos, entradas inválidas y soltar botones.

**Decisión:** ver `docs/adr/0002-cliente-movil-pygbag.md`.

## Reglas para el cliente real

Están en el ADR 0002. En resumen: ciclo principal `async`, nada bloqueante, red y entradas detrás
de interfaces (`red.py`, `entrada.py`), imports de escritorio dentro de sus clases y `pygame-ce`
en las dos plataformas.
