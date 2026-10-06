# Hardware

Control físico de 5 botones con Arduino: arriba, abajo, izquierda, derecha y acción.
Se conecta por USB Serial a la computadora del jugador; el cliente pygame traduce las señales y
las envía al servidor por WebSocket.

- `simulator/`: simulador del control para probar sin el Arduino.
- `firmware/`: código del Arduino (se agrega cuando exista el prototipo).

Mensajes, pines y protocolo: [`docs/contrato-api-hardware.md`](../docs/contrato-api-hardware.md).
