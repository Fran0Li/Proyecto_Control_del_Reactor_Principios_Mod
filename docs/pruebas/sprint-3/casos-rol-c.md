# Casos de prueba del Sprint 3 — Rol C (US-10, US-26 y US-11)

Cubre el control físico (US-10), el aviso de control desconectado (US-26, parte de la US-10) y la
extracción de energía del reactor con el botón de acción (US-11). Tasks del Board: AB#114 y AB#115.
La numeración del rol C en el Sprint 3 va de CP-265 a CP-314 (rol A: CP-165 a CP-214; rol B:
CP-215 a CP-264).

**Tipos:** **U** unitaria (una pieza sola, sin base de datos ni red), **I** integración (varias
piezas juntas: el canal WebSocket con el motor y la base de datos, o el adaptador Serial con los
controles y el aviso) y **A** aceptación (el juego completo con la placa real, a mano). **CI**
indica que lo comprueba un paso del pipeline de GitHub Actions en cada Pull Request.

Archivos: `s/` = `server/tests/`, `c/` = `client/tests/`, `fw/` = `hardware/firmware/pruebas/`.

## Resumen

| Historia | Casos | OK | Pendiente |
| --- | --- | --- | --- |
| US-10 Mover el personaje con el control físico | CP-265 a CP-275 (11) | 10 | 1 (CP-274) |
| US-26 Aviso de control desconectado | CP-276 a CP-285 (10) | 9 | 1 (CP-285) |
| US-11 Extraer energía del reactor | CP-286 a CP-301 (16) | 15 | 1 (CP-301) |
| **Total** | **37** | **34** | **3** |

Los tres pendientes son de aceptación con la placa real y se ejecutan a mano (ver
[Cómo ejecutar los casos de aceptación](#cómo-ejecutar-los-casos-de-aceptación)).

## US-10 Mover el personaje con el control físico

**Criterios de aceptación (ERS):** el personaje se mueve en pantalla según el botón físico
presionado; el movimiento se refleja en menos de 500 ms; el panel tiene como mínimo los botones de
arriba, abajo, izquierda y derecha.

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-265 | El panel tiene las 4 direcciones y la acción | Firmware de 5 botones, pines D2 a D6 con `INPUT_PULLUP` | Presionar y soltar cada botón | `BTN UP`, `DOWN`, `LEFT`, `RIGHT` y `ACTION` con `PRESS` y `RELEASE` | OK | U, CI | `fw/prueba_firmware.cpp` (regresión de CP-139) |
| CP-266 | El cliente convierte los botones en entradas | Puerto falso | `HELLO`, `BTN UP PRESS` y `BTN UP RELEASE` | Estado `conectado` y las entradas `arriba` / `presionado` y `arriba` / `liberado` | OK | U | `c/test_entrada_serial.py::test_saludo_conecta_y_botones_generan_entradas` |
| CP-267 | El control físico manda el mismo mensaje que el teclado | — | Izquierda desde el teclado y desde el control | Mensajes iguales salvo `origen` (`teclado` y `hardware`) | OK | U | `c/test_entradas_jugador.py::test_mismo_mensaje_desde_teclado_y_desde_el_control_fisico` |
| CP-268 | Con `CONTROL_PUERTO` se agrega el control físico | Cliente de escritorio | Puerto configurado y sin configurar | Con puerto: teclado y `EntradaSerial`; sin puerto: solo teclado | OK | U | `c/test_entradas_jugador.py::test_en_escritorio_con_puerto_agrega_el_control_fisico`, `c/test_entradas_jugador.py::test_en_escritorio_sin_puerto_solo_teclado` |
| CP-269 | Cada botón mueve hacia su lado | Jugador en la partida | `arriba`, `abajo`, `izquierda` y `derecha` presionados | El jugador avanza en la dirección del botón | OK | U | `s/test_motor_partida.py::test_cada_direccion_mueve_hacia_su_lado` |
| CP-270 | Soltar el botón detiene al jugador | Jugador moviéndose | `liberado` | El jugador se detiene | OK | U | `s/test_motor_partida.py::test_soltar_el_control_detiene_al_jugador` |
| CP-271 | El movimiento llega a todos los jugadores | Partida con dos jugadores conectados por WebSocket | Un jugador presiona una dirección | Los dos clientes reciben la nueva posición | OK | I | `s/test_movimiento_ws.py::test_presionar_una_direccion_mueve_al_jugador_y_avisa`, `s/test_movimiento_ws.py::test_todos_los_jugadores_ven_el_movimiento_de_los_demas` |
| CP-272 | El servidor devuelve la posición en menos de 500 ms | Partida con dos jugadores | El cliente manda `derecha` / `presionado` | La nueva posición llega antes de 0,5 s | OK | I | `s/test_movimiento_ws.py::test_la_posicion_llega_a_los_clientes_en_menos_de_500_ms` |
| CP-273 | Mover el personaje con la placa real | Arduino Uno en COM5 con el firmware cargado, backend local, cliente con `CONTROL_PUERTO=COM5` | Presionar arriba, abajo, izquierda y derecha en la arena | Aparece el aviso verde "Control conectado." y el personaje se mueve hacia el lado de cada botón | OK | A | Manual, 14/11/2026 |
| CP-274 | Latencia de punta a punta con la placa (< 500 ms) | Igual que CP-273 | 10 presiones de un botón, grabadas en video | Del botón hundido al personaje moviéndose pasan menos de 500 ms en todas las presiones | **Pendiente** | A | Manual (procedimiento abajo) |
| CP-275 | Sin el control, el juego sigue con el teclado | `CONTROL_PUERTO` apunta a un puerto que no existe | Arrancar el cliente | El cliente no se cae, queda `desconectado` y se juega con el teclado | OK | U | `c/test_entrada_serial.py::test_puerto_que_no_existe_no_rompe_el_cliente` (regresión de CP-151) |

## US-26 Aviso de control desconectado

**Qué se comprueba:** si el juego espera un control físico y no lo tiene, el jugador lo ve en la
arena (aviso naranja fijo, con la indicación de que puede seguir con el teclado); al conectarse, ve
la confirmación en verde durante 3 s. La detección de la desconexión (3 s sin `HB` o error al leer
el puerto) ya la hacía `EntradaSerial` desde el Sprint 2 (CP-148 y CP-150).

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-276 | Sin control físico no hay aviso | Cliente sin `CONTROL_PUERTO` | Estado del control: ninguno | No se muestra ningún aviso | OK | U | `c/test_aviso_control.py::test_sin_control_fisico_no_hay_aviso` |
| CP-277 | Mientras espera al control, avisa que se puede usar el teclado | Puerto configurado | Estado `desconectado` y luego `abierto` (sin datos) | Aviso naranja "Esperando el control físico... Podés jugar con el teclado." | OK | U | `c/test_aviso_control.py::test_mientras_espera_al_control_avisa_que_se_puede_usar_el_teclado` |
| CP-278 | Al conectar, confirma y después desaparece | Puerto abierto | Estado `conectado`; pasan 3 s | Aviso verde "Control conectado." que desaparece a los 3 s | OK | U | `c/test_aviso_control.py::test_al_conectar_confirma_unos_segundos_y_luego_desaparece` |
| CP-279 | Si se desconecta, el aviso queda fijo | Control conectado | Estado `desconectado`; pasan 60 s | Aviso naranja "Control desconectado. Seguí con el teclado; se reconecta solo." todo el tiempo | OK | U | `c/test_aviso_control.py::test_si_se_desconecta_despues_de_conectar_lo_dice_y_no_desaparece` |
| CP-280 | Al reconectar vuelve a confirmar | Control desconectado | Estado `conectado` | Aviso verde "Control conectado." | OK | U | `c/test_aviso_control.py::test_al_reconectar_vuelve_a_confirmar` |
| CP-281 | Desconexión y reconexión de punta a punta en el cliente | `EntradaSerial` con puerto y reloj falsos, `ControlesJugador` y `AvisoControl` | `HELLO`; 3 s sin `HB`; reintento y `HB` | Naranja → verde → naranja; el servidor recibe `dispositivo: desconectado`; al reintentar vuelve a verde | OK | I | `c/test_aviso_control.py::test_el_jugador_ve_la_desconexion_y_la_reconexion_del_control` |
| CP-282 | Con el cable desconectado avisa de inmediato | Control conectado | Error al leer el puerto | Aviso naranja sin esperar los 3 s | OK | I | `c/test_aviso_control.py::test_con_el_cable_desconectado_avisa_de_inmediato` |
| CP-283 | La arena dibuja el aviso arriba al centro | Pantalla de la arena con control físico configurado | Un cuadro de la arena | El píxel de arriba al centro tiene el color de alerta | OK | U | `c/test_aviso_control.py::test_la_arena_dibuja_el_aviso_arriba_al_centro`, `c/test_aviso_control.py::test_sin_control_fisico_la_arena_no_muestra_aviso` |
| CP-284 | Aviso al conectar la placa real | Igual que CP-273 | Entrar a la arena con la placa conectada | Aviso verde "Control conectado." durante unos segundos | OK | A | Manual, 14/11/2026 |
| CP-285 | Desconectar el cable en plena partida | Igual que CP-273, personaje moviéndose | Desconectar el cable USB y volver a conectarlo | Al desconectar: aviso naranja fijo y el personaje se detiene (no queda un botón pegado); se puede seguir con el teclado. Al reconectar: aviso verde y los botones vuelven a responder sin reiniciar el juego | **Pendiente** | A | Manual (procedimiento abajo) |

## US-11 Extraer energía del reactor

**Criterios de aceptación (ERS):** la extracción solo ocurre al presionar el botón físico de
acción, no automáticamente; solo es posible si el jugador está en la posición del reactor; la
energía extraída se suma al puntaje del jugador.

**Reglas implementadas:** cada presión saca hasta 10 de energía; cada jugador espera 0,5 s entre
extracciones; el reactor guarda hasta 100 de energía, compartida entre todos, y se recarga 5 por
segundo. El jugador está "en el reactor" cuando lo toca: distancia entre centros menor o igual al
radio del reactor más el del jugador (60 px).

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-286 | Extraer tocando el reactor | Reactor lleno (100) | Un jugador en el reactor intenta extraer | Recibe 10 y el reactor queda en 90 | OK | U | `s/test_reactor.py::test_extraer_tocando_el_reactor_da_energia_y_la_descuenta` |
| CP-287 | Solo extrae quien toca el reactor (límite) | Reactor lleno | Jugador a 60 px y a 61 px del centro | A 60 px extrae; a 61 px no | OK | U | `s/test_reactor.py::test_solo_extrae_quien_esta_tocando_el_reactor` |
| CP-288 | Soltar el botón no extrae | Jugador en el reactor | `accion` / `liberado` | El puntaje sigue en 0 | OK | U | `s/test_reactor.py::test_soltar_la_accion_no_extrae` |
| CP-289 | Lejos del reactor la acción no da puntos | Jugador 2 en (100, 100) | `accion` / `presionado` | El puntaje del jugador 2 sigue en 0 | OK | U | `s/test_reactor.py::test_lejos_del_reactor_la_accion_no_da_puntos` |
| CP-290 | Hay que esperar 0,5 s entre extracciones | Jugador en el reactor | Extraer a los 0 s, 0,49 s y 0,5 s | Extrae a los 0 s y 0,5 s; a los 0,49 s no | OK | U | `s/test_reactor.py::test_hay_que_esperar_entre_una_extraccion_y_la_siguiente` |
| CP-291 | La espera es de cada jugador | Dos jugadores en el reactor | Los dos extraen a los 0 s | Los dos extraen | OK | U | `s/test_reactor.py::test_la_espera_es_de_cada_jugador` |
| CP-292 | Presionar muy seguido no da más puntos | Jugador en el reactor | 5 presiones seguidas en el mismo instante | Suma 10, no 50 | OK | U | `s/test_reactor.py::test_presionar_muy_seguido_no_da_mas_puntos` |
| CP-293 | La espera corre con los ticks del motor | Jugador en el reactor | Presionar, avanzar 0,5 s en ticks y presionar otra vez | Suma 20 | OK | U | `s/test_reactor.py::test_la_espera_corre_con_los_ticks_del_motor` |
| CP-294 | Con poca energía se extrae lo que queda | Reactor con 15 y sin recarga | Tres jugadores extraen | 10, 5 y nada; el reactor queda en 0 | OK | U | `s/test_reactor.py::test_con_poca_energia_se_extrae_lo_que_queda_y_vacio_no_da_nada` |
| CP-295 | El reactor se recarga hasta su capacidad | Reactor vacío con capacidad 20 | Pasa 1 s y luego 60 s | 5 al segundo; nunca más de 20 | OK | U | `s/test_reactor.py::test_el_reactor_se_recarga_con_el_tiempo_hasta_su_capacidad`, `s/test_reactor.py::test_actualizar_avisa_solo_cuando_cambia_la_energia_entera` |
| CP-296 | La energía extraída se suma al puntaje | Jugador en el reactor, puntaje 0 | `accion` / `presionado` | Puntaje 10; `estado["reactor"]["energia"]` = 90 | OK | U | `s/test_reactor.py::test_presionar_la_accion_en_el_reactor_suma_puntos` |
| CP-297 | La acción no mueve al jugador | Jugador quieto | `accion` / `presionado` | La posición no cambia | OK | U | `s/test_motor_partida.py::test_la_accion_no_mueve_al_jugador` |
| CP-298 | El motor avisa la extracción a los observadores | Observador suscrito | Extracción | Evento `accion_realizada` (jugador, `reactor`, 10) y después `estado_actualizado` | OK | U | `s/test_reactor.py::test_la_extraccion_avisa_la_accion_y_luego_el_estado` |
| CP-299 | Los jugadores ven la recarga del reactor | Reactor por debajo de su capacidad | Pasa 1 s | Los estados enviados muestran la energía subiendo | OK | U | `s/test_reactor.py::test_mientras_el_reactor_se_recarga_los_jugadores_lo_ven` |
| CP-300 | Acciones nuevas sin tocar el motor (abierto/cerrado) | Motor con una acción falsa antes del reactor | `accion` / `presionado` | Se usa la primera acción que aplica | OK | U | `s/test_reactor.py::test_el_motor_prueba_las_acciones_en_orden_y_usa_la_primera_que_aplica` |
| CP-301 | Extraer con el botón físico de acción | Igual que CP-273; la arena dibuja el reactor y el HUD muestra el puntaje (US-24) | 1) Quedarse 5 s sobre el reactor sin presionar. 2) Presionar el botón de acción (D6). 3) Presionar lejos del reactor | 1) El puntaje no cambia. 2) Suma 10 y la barra del reactor baja. 3) No suma | **Pendiente** | A | Manual (procedimiento abajo) |

Además, por WebSocket con dos jugadores: la acción junto al reactor le suma 10 a quien la hizo, el
otro jugador lo ve y el reactor queda por debajo de su capacidad
(`s/test_movimiento_ws.py::test_la_accion_junto_al_reactor_suma_puntos_y_todos_lo_ven`). Se cuenta
dentro de CP-296 y CP-298 porque comprueba lo mismo de punta a punta.

## Cómo ejecutar los casos de aceptación

1. Cargar el firmware (`hardware/firmware/control_reactor/control_reactor.ino`) en el Arduino Uno y
   cerrar el Monitor Serie del Arduino IDE (si queda abierto, ocupa el puerto).
2. En la raíz del repo: `docker compose up` y esperar `Application startup complete`.
3. En `client/`: `$env:CONTROL_PUERTO="COM5"` y `python main.py` (o `.\jugar.ps1 -Puerto COM5`).
4. Iniciar sesión, crear una partida y entrar a la arena.

**CP-274 (latencia):** grabar con el celular en cámara lenta (o a 60 fps) la mano en el control y la
pantalla en el mismo encuadre. Presionar un botón de dirección 10 veces. En el video, contar los
cuadros entre el momento en que se hunde el botón y el primer cuadro en que el personaje se mueve, y
convertir a milisegundos (a 60 fps, 1 cuadro ≈ 16,7 ms; a 240 fps, ≈ 4,2 ms). Anotar el promedio y el
máximo; el caso pasa si el máximo es menor que 500 ms.

**CP-285 (desconexión):** con el personaje moviéndose (botón presionado), desconectar el cable USB.
Revisar el aviso naranja, que el personaje se detenga y que el teclado siga funcionando. Volver a
conectar el cable y esperar unos segundos: aviso verde y los botones responden otra vez.

**CP-301 (extracción):** en la arena, caminar hasta tocar el reactor y seguir el orden de la columna
Entrada. Revisar el puntaje del jugador y la barra de energía del reactor. Al 16/11/2026 el cliente
todavía no dibuja el reactor ni el puntaje: este caso se ejecuta cuando estén la arena visual y el
HUD (US-24).

Evidencia: captura o video de cada caso en la Wiki, página "Casos de prueba" del Sprint 3.

## Regresión

Las pruebas automáticas que cubren el control y el movimiento desde el Sprint 2 (CP-137 a CP-154 y
los casos de movimiento de la US-25) se vuelven a ejecutar en cada Pull Request en el CI, junto con
las de este documento. Ejecución del 16/11/2026 sobre `develop` (`05d70da`, después de mergear el
PR #50): **263 pruebas del servidor, 193 del cliente y las del firmware pasan**, sin fallos.

Para repetirlas: `python -m pytest -q` dentro de `server/` y de `client/` (el cliente con
`SDL_VIDEODRIVER=dummy`), y el firmware con los comandos de `hardware/firmware/README.md`.
