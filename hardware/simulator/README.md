# Simulador del control

`simulador.py` abre una ventana con los 5 botones y envía por un socket local las **mismas líneas**
que el Arduino envía por USB (`HELLO`, `BTN …`, `HB`). El cliente lo abre igual que un puerto
serial, con la dirección `socket://localhost:7777`, así que todo lo que está después del puerto se
prueba sin hardware.

## Uso

```
pip install pygame-ce
python simulador.py
```

Con la ventana del simulador seleccionada:

| Tecla | Control |
| --- | --- |
| Flechas o WASD | Direcciones |
| Espacio | Acción |
| Clic en los botones | Igual que las teclas |
| H | Pausar o reanudar los latidos, para probar la desconexión |

## Probarlo con el juego

Con el prototipo de `prototipos/cliente-movil` (servidor de prueba corriendo):

```
$env:CONTROL_PUERTO="socket://localhost:7777"; python main.py
```

Al presionar botones en el simulador, el jugador de ese cliente se mueve y aparece con origen
`simulador`. Al pausar los latidos con H, a los 3 s el cliente suelta los controles y muestra
"Control físico: desconectado"; al reanudarlos, se reconecta solo.
