# Hardware

Control físico con Arduino: movimiento (joystick o 4 botones) y botón de acción. Se conecta por
USB Serial a la computadora del jugador; el cliente traduce las señales y las envía al servidor por
WebSocket.

| Carpeta | Contenido |
| --- | --- |
| `firmware/` | Código del Arduino, instrucciones para Tinkercad y pruebas del firmware en la PC |
| `simulator/` | Simulador del control: envía los mismos mensajes sin hardware |

El lado del cliente está en `client/src/entrada/` (`EntradaSerial`), con sus pruebas en
`client/tests/`.

Mensajes, pines y protocolo: [`docs/contrato-api-hardware.md`](../docs/contrato-api-hardware.md).
