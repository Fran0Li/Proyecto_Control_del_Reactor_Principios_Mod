# Hardware

Control físico con Arduino de 5 botones (arriba, abajo, izquierda, derecha y acción); el firmware
admite también joystick para más adelante. Se conecta por USB Serial a la computadora del jugador
y el cliente traduce las señales y las envía al servidor por WebSocket.

| Carpeta | Contenido |
| --- | --- |
| `firmware/` | Código del Arduino, instrucciones para Tinkercad y pruebas del firmware en la PC |
| `simulator/` | Simulador del control: envía los mismos mensajes sin hardware |

El lado del cliente está en `client/src/entrada/` (`EntradaSerial`), con sus pruebas en
`client/tests/`.

Mensajes, pines y protocolo: [`docs/contrato-api-hardware.md`](../docs/contrato-api-hardware.md).
