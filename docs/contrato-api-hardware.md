# Contrato de la API de hardware

Define cómo llegan al servidor las señales del control físico de 5 botones (RNF-10) y cómo se
mapean al mismo comando que usa el movimiento por teclado (RF-010, RF-026, CU-07).

Estado: **propuesta v1, Sprint 2**. Los mensajes de la capa 2 (WebSocket) se validan con el
responsable de US-25 antes de implementarlos.

## Resumen

```
[Control Arduino] --USB Serial--> [Cliente pygame] --WebSocket--> [Servidor FastAPI]
  5 botones          líneas de       adaptador de        mensajes JSON     motor de partida
                     texto ASCII     entrada                               (posiciones, acción)
```

- El Arduino solo lee botones y avisa cuándo se presionan o se liberan.
- El cliente pygame lee el puerto serial y traduce cada señal al **mismo mensaje** que genera
  el teclado. Para el servidor no hay diferencia entre teclado, control físico o simulador.
- El servidor es el que decide el movimiento, las colisiones y la acción (servidor autoritativo).

### Por qué este protocolo

| Opción | Ventaja | Desventaja |
| --- | --- | --- |
| **Serial (USB) + WebSocket del cliente** ✅ | Funciona con cualquier Arduino (Uno, Nano), sin WiFi; reutiliza la conexión y la autenticación que el cliente ya tiene | El control debe estar conectado a la computadora del jugador |
| WebSocket directo desde el dispositivo | El control no depende de la computadora | Requiere placa con WiFi (ESP32) y autenticar el dispositivo por separado |
| MQTT | Bueno para muchos dispositivos | Agrega un broker más al despliegue, innecesario para este alcance |

Si más adelante se usa una placa con WiFi, solo cambia la capa 1: el dispositivo enviaría los
mensajes de la capa 2 directamente al servidor.

## Hardware

| Botón | Control | Pin Arduino |
| --- | --- | --- |
| Arriba | `arriba` | D2 |
| Abajo | `abajo` | D3 |
| Izquierda | `izquierda` | D4 |
| Derecha | `derecha` | D5 |
| Acción | `accion` | D6 |

- Cada botón va entre su pin y GND, con `INPUT_PULLUP` (sin resistencias externas).
  Presionado = `LOW`.
- Antirrebote (debounce) por software de **20 ms**.
- LED integrado (D13) encendido mientras el control está enviando latidos (opcional).

**Variante con joystick** (pendiente de confirmar con el Product Owner, porque RNF-10 pide cinco
botones): VRx → A0, VRy → A1, clic del joystick (SW) → D7 y botón de acción en D6. El firmware
convierte la palanca en los mismos mensajes `BTN UP/DOWN/LEFT/RIGHT`, con histéresis y diagonales,
así que la capa 1 y todo lo que sigue no cambian. Detalle en `hardware/firmware/README.md`.

## Capa 1: Arduino → computadora (Serial)

- USB Serial a **115200 baudios, 8N1**.
- Mensajes de texto ASCII, **uno por línea**, terminados en `\n`. Mayúsculas, separados por un
  espacio.

| Mensaje | Cuándo | Ejemplo |
| --- | --- | --- |
| `HELLO <id> <version>` | Al encender o reiniciar | `HELLO CR-PAD-01 1.0` |
| `BTN <boton> PRESS` | Un botón pasa a presionado | `BTN UP PRESS` |
| `BTN <boton> RELEASE` | Un botón se suelta | `BTN UP RELEASE` |
| `HB` | Latido, cada 1 s | `HB` |

Valores de `<boton>`: `UP`, `DOWN`, `LEFT`, `RIGHT`, `ACTION`.

Reglas:
- Solo se envían **cambios de estado**, no el estado de cada botón todo el tiempo.
- Una línea que no cumple el formato se **descarta** y se registra en el log del cliente
  (CU-07, excepción E1).
- Mantener presionado un direccional no repite mensajes: el `PRESS` dura hasta el `RELEASE`.

## Capa 2: cliente → servidor (WebSocket)

Conexión al canal de la partida (lo implementa US-08):

```
ws://<host>:8000/ws/partidas/{partida_id}?token=<JWT>
```

Todos los mensajes son JSON con un campo `tipo`.

### Cliente → servidor

**Entrada de control** (teclado, control físico o simulador):

```json
{
  "tipo": "entrada",
  "control": "arriba",
  "estado": "presionado",
  "origen": "hardware",
  "seq": 128
}
```

| Campo | Valores | Notas |
| --- | --- | --- |
| `control` | `arriba`, `abajo`, `izquierda`, `derecha`, `accion` | |
| `estado` | `presionado`, `liberado` | |
| `origen` | `teclado`, `hardware`, `simulador` | Solo informativo (estadísticas, pruebas) |
| `seq` | entero creciente | Número de secuencia por conexión; el servidor descarta mensajes repetidos o atrasados |

**Estado del dispositivo** (para mostrar en la interfaz si el control está conectado):

```json
{ "tipo": "dispositivo", "estado": "conectado", "id": "CR-PAD-01" }
```

`estado`: `conectado` o `desconectado`.

### Servidor → cliente

El mensaje de estado de la partida (posiciones de todos los jugadores) lo define US-25. Para
esta integración solo se agrega el mensaje de error:

```json
{ "tipo": "error", "codigo": "entrada_invalida", "detalle": "control desconocido: saltar" }
```

### Cómo interpreta el servidor las entradas

- Guarda, por jugador, qué direccionales están presionados.
- En cada ciclo del motor de partida mueve al jugador según esos direccionales y valida
  colisiones (US-25).
- `accion` + `presionado` dispara la acción del contexto: extraer energía, activar una
  terminal, etc. (RF-011, RF-012, Sprint 3). `accion` + `liberado` se ignora en este sprint.
- Si el jugador está "Aturdido" o "Eliminado temporalmente", ignora sus entradas (CU-07, E3).
- Una entrada con campos inválidos se descarta y se responde con `error` (CU-07, E1).
- Límite de **30 entradas por segundo** por jugador; lo que pase de ahí se descarta.

## Mapeo entre fuentes de entrada

| Control | Teclado (pygame) | Serial | Mensaje WebSocket |
| --- | --- | --- | --- |
| Arriba | `K_UP` / `K_w` | `BTN UP PRESS` / `RELEASE` | `"control": "arriba"` |
| Abajo | `K_DOWN` / `K_s` | `BTN DOWN …` | `"control": "abajo"` |
| Izquierda | `K_LEFT` / `K_a` | `BTN LEFT …` | `"control": "izquierda"` |
| Derecha | `K_RIGHT` / `K_d` | `BTN RIGHT …` | `"control": "derecha"` |
| Acción | `K_SPACE` | `BTN ACTION …` | `"control": "accion"` |

`KEYDOWN` equivale a `presionado` y `KEYUP` a `liberado`.

En el cliente, el teclado, el puerto serial y el simulador implementan una misma interfaz de
"fuente de entrada" que produce estos mensajes (patrón Adapter, ver ADRs de patrones).

## Desconexión y reconexión

- Si el cliente no recibe ningún mensaje del Arduino durante **3 s**, lo considera desconectado:
  1. Envía `liberado` para cada control que estuviera presionado, para que el personaje no se
     quede moviendo solo.
  2. Envía `{"tipo": "dispositivo", "estado": "desconectado"}`.
  3. Sigue funcionando con teclado (RF-026, CU-08 excepción E2).
- El cliente reintenta abrir el puerto serial cada **2 s**. Al recibir `HELLO` envía
  `dispositivo: conectado`.
- Si se cae el WebSocket, el cliente reintenta la conexión; al reconectar, el servidor
  considera todos los controles de ese jugador como liberados.

## Latencia (RNF-02: menos de 500 ms)

| Tramo | Tiempo estimado |
| --- | --- |
| Antirrebote en el Arduino | 20 ms |
| Serial USB a 115200 baudios | < 5 ms |
| Cliente → servidor (WebSocket en red local) | < 50 ms |
| Ciclo del motor de partida | ≤ 50 ms |
| Difusión a los clientes | < 50 ms |
| **Total** | **≈ 175 ms** |

## Simulador

`hardware/simulator/simulador.py` emite exactamente las mismas líneas de la capa 1 por un socket
local. El cliente lo abre como si fuera un puerto serial, con `socket://localhost:7777` en lugar de
`COM3`, y marca sus entradas con `origen: "simulador"`. Uso en `hardware/simulator/README.md`.

## Pruebas

| Caso | Entrada | Resultado esperado |
| --- | --- | --- |
| Línea válida | `BTN LEFT PRESS` | Entrada `izquierda` / `presionado` |
| Línea inválida | `BTN JUMP PRESS` | Se descarta, se registra en el log |
| Latido perdido | Sin mensajes por 3 s | Controles liberados y dispositivo desconectado |
| Reconexión | `HELLO CR-PAD-01 1.0` después de una desconexión | Dispositivo conectado |
| Entrada inválida al servidor | `"control": "saltar"` | Respuesta `error` con `entrada_invalida` |
| Jugador aturdido | Entrada `arriba` | El servidor la ignora |
| Fuente indistinta | Misma secuencia por teclado y por Serial | Mismo movimiento en el servidor |
