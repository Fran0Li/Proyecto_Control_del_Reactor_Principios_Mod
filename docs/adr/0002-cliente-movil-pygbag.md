# ADR 0002: Cliente móvil con pygbag

- **Estado:** Aceptado
- **Fecha:** 2026-10-09
- **Relacionado:** ADR 0001 (stack), `docs/contrato-api-hardware.md`, `prototipos/cliente-movil/`

## Contexto

El profesor confirmó que la versión móvil es obligatoria (RNF-07). El ADR 0001 eligió pygame
para el cliente, pero pygame no corre de forma nativa en Android ni iOS. El equipo es de tres
personas y no quiere mantener dos clientes completos en lenguajes distintos.

## Opciones evaluadas

| Opción | Ventaja | Desventaja |
| --- | --- | --- |
| **pygbag: el mismo cliente pygame compilado a WebAssembly** | Un solo código para PC y móvil, todo en Python; se abre desde el navegador sin instalar nada | Obliga a programar el cliente con un ciclo `async` y sin llamadas bloqueantes |
| Cliente web aparte (HTML/JavaScript) | Funciona en cualquier celular | Es un segundo cliente completo, en otro lenguaje |
| App nativa con Kivy o BeeWare | Genera un APK instalable | Compilar para Android desde Windows es complejo; otro framework distinto de pygame |

## Prueba técnica

Se construyó un prototipo en `prototipos/cliente-movil/` (work item 89) con un servidor de prueba
que implementa el contrato de entradas. Resultados del 09/10/2026:

| Prueba | Resultado |
| --- | --- |
| pygbag compila y la página carga en el navegador de la PC | ✅ |
| La página carga en el celular (Chrome Android, mismo WiFi) | ✅ |
| Conexión WebSocket desde el navegador al servidor | ✅ |
| Botones táctiles mueven al jugador | ✅ (después de la corrección de abajo) |
| PC y celular conectados a la vez se ven en tiempo real | ✅ 3 jugadores simultáneos |
| El jugador se detiene al soltar el botón | ✅ (después de la corrección de abajo) |
| Latencia ida y vuelta | ✅ 16 ms en el navegador de la PC, 33 ms en el celular (límite: 500 ms) |

**Problema encontrado:** en el celular un botón podía quedarse presionado, porque el navegador a
veces cancela el toque y no llega el evento de soltar. Se corrigió revisando en cada frame qué dedos
siguen tocando la pantalla y soltando los botones que ya no tienen dedo.

## Decisión

El cliente del juego se mantiene en pygame y se publica en dos formas desde el mismo código:

- **Escritorio:** se ejecuta con Python, con teclado y control Arduino.
- **Móvil:** se compila con pygbag y se abre desde el navegador, con botones táctiles en pantalla.

El backend no cambia: todas las fuentes de entrada envían el mismo mensaje `entrada` del contrato,
con `origen` igual a `teclado`, `hardware`, `simulador` o `tactil`.

## Reglas para el cliente

1. El ciclo principal es `async def main()` y hace `await asyncio.sleep(0)` en cada frame.
2. Nada bloqueante en el cliente: ni `requests`, ni `time.sleep`, ni sockets directos en las
   pantallas ni en el ciclo principal.
3. La red va detrás de una interfaz con una implementación para escritorio y otra para navegador:
   - REST: en escritorio `requests` dentro de un hilo (`asyncio.to_thread`); en el navegador el
     `fetch` del navegador. Está en `client/src/red/http.py`.
   - Tiempo real: en escritorio la librería `websockets`; en el navegador el `WebSocket` del
     navegador, como en `prototipos/cliente-movil/red.py`.

   En el navegador, `fetch` y `WebSocket` se usan desde Python con `platform.window` de pygbag, que
   ejecuta pequeñas instrucciones de JavaScript en la página. El cliente sigue siendo Python y
   pygame: no se agrega otro lenguaje ni otro framework al stack del ADR 0001.
4. Las entradas usan la interfaz de fuente de entrada (patrón Adapter): teclado, táctil y Arduino.
   La táctil incluye la revisión por frame de botones pegados.
5. Las librerías que solo existen en escritorio (`requests`, `websockets`, `pyserial`) se importan
   dentro de la función o clase de escritorio, para que pygbag no intente instalarlas.
6. Se usa **pygame-ce** también en escritorio, porque es la versión que trae pygbag.

## Consecuencias

- El cliente de US-07, US-08 y US-25 se construye siguiendo estas reglas desde ahora.
- Para que el celular se conecte, el backend tiene que ser accesible desde la red: en red local
  para pruebas y en la nube para el Sprint 3 (RNF-09).
- Si la página se publica por HTTPS, el WebSocket tiene que ser `wss://`, así que el backend en la
  nube necesita certificado TLS.
- El backend permite CORS (`CORS_ORIGENES`) porque la página de pygbag (puerto 8001) llama a la
  API (puerto 8000), que para el navegador es otro origen.
- Al servir la versión web con el servidor de pruebas de pygbag hay que usar la IP real de la PC en
  `--bind`, no `0.0.0.0`.
- La primera carga en el celular tarda unos segundos porque descarga el motor de Python.
