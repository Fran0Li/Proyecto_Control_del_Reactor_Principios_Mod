# Sprites del juego

Pixel art de 30 x 30 (estilo futurista). Los carga `src/sprites.py`; si falta una imagen, el
juego dibuja la figura de antes (círculo o rectángulo).

| Archivo | Se usa para |
| --- | --- |
| `jugador_1.png` a `jugador_4.png` | El personaje de cada jugador según su número (1 a 4). En la arena se dibuja a 32 x 32 dentro del aro de su color |
| `muro.png` | Relleno de las barreras fijas y móviles, en cuadros de 30 x 30 (los obstáculos de los escenarios miden múltiplos de 30) |
| `guardian.png` | Los guardianes (US-15): se tiñe de morado y va a 32 x 32 dentro de su aro morado oscuro |
| `extra/` | Disponibles para lo que falta (reactor, terminales): base, torres y unidad rápida |

## Efectos

Cuando un guardián alcanza a un jugador (pasa a aturdido), la arena lanza chispas y una onda
morada en ese punto. No usan imágenes de esta carpeta: las dibuja `src/screens/particulas.py`
(patrón Flyweight, `docs/adr/0012-flyweight-particulas.md`).
