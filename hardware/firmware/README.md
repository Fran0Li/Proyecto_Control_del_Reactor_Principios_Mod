# Firmware del control físico

`control_reactor/control_reactor.ino` lee el control y envía por USB Serial los mensajes del
contrato (`docs/contrato-api-hardware.md`): `HELLO`, `BTN <boton> PRESS|RELEASE` y `HB`.

Tiene dos formas de armado. Se elige con `USAR_JOYSTICK` al inicio del archivo:

| `USAR_JOYSTICK` | Movimiento | Acción |
| --- | --- | --- |
| `0` (por defecto) | 4 botones: arriba D2, abajo D3, izquierda D4, derecha D5 | Botón en D6 |
| `1` | Joystick analógico: VRx → A0, VRy → A1 | Botón en D6; clic del joystick (SW) en D7 |

Con joystick (opción para más adelante), el firmware convierte la palanca en los mismos mensajes
que los botones (con diagonales), así que el cliente y el servidor no cambian.

- Botones entre el pin y GND, con `INPUT_PULLUP`: no llevan resistencias.
- Antirrebote de 20 ms. Con joystick, histéresis: se activa al pasar de 300 y se suelta al bajar
  de 200 (sobre 512), para que no tiemble cerca del borde.
- Si una dirección del joystick real sale al revés, cambiar `INVERTIR_X` o `INVERTIR_Y`.
- LED integrado (D13) encendido mientras el control funciona.

## Probar en Tinkercad

1. Arduino Uno R3 y protoboard. **GND** del Arduino al riel **−** de la protoboard.
2. Cinco pulsadores (*Pushbutton*) cruzando el canal central de la protoboard.
3. De cada pulsador, una pata a su pin y la pata contraria (en diagonal) al riel GND:
   arriba **D2**, abajo **D3**, izquierda **D4**, derecha **D5**, acción **D6**. Sin resistencias.
4. **Code → Text**, pegar `control_reactor.ino`, **Start Simulation** y abrir el **Serial Monitor**.

Resultado esperado: `HELLO CR-PAD-01 1.0` al arrancar, `HB` cada segundo y, al mantener
presionado un botón, `BTN UP PRESS` (o el que corresponda); al soltarlo, `BTN UP RELEASE`.

**Versión con joystick:** Tinkercad no tiene joystick; se simula con dos potenciómetros (extremos a
GND y 5V, pata del medio a A0 y A1), cambiando `USAR_JOYSTICK` a `1`.

## Probar con el Arduino real

1. Cargar `control_reactor.ino` con el Arduino IDE (placa Arduino Uno o Nano).
2. Abrir el Monitor Serie a **115200 baudios** y comprobar los mensajes.
3. **Cerrar el Monitor Serie** (el puerto solo lo puede usar un programa a la vez).
4. Correr el cliente con el puerto del Arduino, por ejemplo en PowerShell:
   ```
   $env:CONTROL_PUERTO="COM3"; python main.py
   ```
   El puerto (`COM3`, `COM4`…) aparece en el Arduino IDE en **Herramientas → Puerto**.

## Pruebas automáticas del firmware

`pruebas/` compila el firmware en la PC con un `Arduino.h` simulado y comprueba los mensajes:
arranque, latidos, joystick con histéresis y diagonales, antirrebote y los 5 botones.

```
cd pruebas
g++ -std=c++17 -Wall prueba_firmware.cpp -o prueba && ./prueba                    # 5 botones
g++ -std=c++17 -Wall -DUSAR_JOYSTICK=1 prueba_firmware.cpp -o prueba && ./prueba   # joystick
```
