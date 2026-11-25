# Sprites del juego

Pixel art de 30 x 30 (estilo futurista). Los carga `src/sprites.py`; si falta una imagen, el
juego dibuja la figura de antes (círculo o rectángulo).

| Archivo | Se usa para |
| --- | --- |
| `jugador_1.png` a `jugador_4.png` | El personaje de cada jugador según su número (1 a 4). En la arena se dibuja a 32 x 32 dentro del aro de su color |
| `muro.png` | Relleno de las barreras fijas y móviles, en cuadros de 30 x 30 (los obstáculos de los escenarios miden múltiplos de 30) |
| `trampa.png` | Las trampas, repetida en cuadros de 30 x 30 dentro de su rectángulo |
| `muro_intermitente.png` | Las puertas: se ven normales cuando están cerradas y oscuras cuando están abiertas (se abren y cierran solas) |
| `guardian.png` | Los guardianes (US-15): se tiñe de morado y va a 32 x 32 dentro de su aro morado oscuro |
| `extra/Base_Futurista.png` | El reactor, el mismo en todos los mapas. Se amplía a 90 x 90 (3 veces), con un halo que late y se apaga con la energía |
| `extra/TorreMagica_Futurista.png` | Las celdas de energía, a 30 x 30 |
| `lab.png` | Fondo del laboratorio |
| `estacion.png` | Fondo de la estación espacial |
| `fabrica.png` | Fondo de la planta industrial |
| `centroinvestigacion.png` | Fondo del centro de investigación |
| `militar.png` | Fondo del complejo militar |
| `fondo_menu.png` | Fondo de todas las pantallas que no son de partida: login, registro, verificar correo, recuperar clave, perfil, lobby, buscar partida y ceremonia. De 960 x 640, la medida de la ventana, con un velo oscuro encima para que el texto se lea |
| `extra/` (el resto) | Sin usar todavía: torre básica, torre pesada y unidad rápida |

Los fondos se ajustan solos a 960 x 540, el tamaño de la arena (`src/screens/dibujo_fondo.py`).
Conviene que sean de esa medida o de la misma proporción (16:9), vistos desde arriba y sin ruido
en el centro, para que se lean el reactor y las celdas. Entre más pesen, más tarda en cargar la
versión del navegador.

## Efectos

Cuando un guardián alcanza a un jugador (pasa a aturdido), la arena lanza chispas y una onda
morada en ese punto. No usan imágenes de esta carpeta: las dibuja `src/screens/particulas.py`
(patrón Flyweight, `docs/adr/0012-flyweight-particulas.md`).