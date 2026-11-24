# Casos de prueba del Sprint 3 — Rol C (US-10, US-26, US-11, US-27 y apoyo a otras historias)

Cubre el control físico (US-10), el aviso de control desconectado (US-26, parte de la US-10) y la
extracción de energía del reactor con el botón de acción (US-11), los logros y los retos (US-27).
Al final están los casos de lo que el rol C hizo para historias de otros roles: los sprites y las
partículas de la arena (US-29), el botón de iniciar con el mínimo de jugadores (US-17), escribir
desde el celular y publicar el login con Google (US-04). Tasks del Board: AB#114, AB#115 y AB#119.
La numeración del rol C en el Sprint 3 va de CP-265 a CP-314 (rol A: CP-165 a CP-214; rol B:
CP-215 a CP-264). Ese rango se llenó, así que los casos nuevos del rol C siguen desde CP-315.

**Tipos:** **U** unitaria (una pieza sola, sin base de datos ni red), **I** integración (varias
piezas juntas: el canal WebSocket con el motor y la base de datos, o el adaptador Serial con los
controles y el aviso) y **A** aceptación (el juego completo con la placa real, a mano). **CI**
indica que lo comprueba un paso del pipeline de GitHub Actions en cada Pull Request.

Archivos: `s/` = `server/tests/`, `c/` = `client/tests/`, `fw/` = `hardware/firmware/pruebas/`.

## Resumen

| Historia | Casos | OK | Pendiente |
| --- | --- | --- | --- |
| US-10 Mover el personaje con el control físico | CP-265 a CP-275 (11) | 11 | — |
| US-26 Aviso de control desconectado | CP-276 a CP-285 (10) | 10 | — |
| US-11 Extraer energía del reactor | CP-286 a CP-301 (16) | 15 | 1 (CP-301) |
| US-27 Logros | CP-302 a CP-318 (17) | 16 | 1 (CP-314) |
| US-27 Retos | CP-319 a CP-329 (11) | 10 | 1 (CP-329) |
| Apoyo a otras historias | CP-330 a CP-345 (16) | 14 | 2 (CP-343, CP-345) |
| **Total** | **81** | **76** | **5** |

Los pendientes son de aceptación y se ejecutan a mano en la demo interna del 25/11, con dos
jugadores en celular y dos en computadora contra la nube: CP-301 (el reactor ya se dibuja desde el
PR #67), CP-314, CP-329, CP-343 y CP-345. Ver
[Cómo ejecutar los casos de aceptación](#cómo-ejecutar-los-casos-de-aceptación).

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
| CP-274 | Latencia de punta a punta con la placa (< 500 ms) | Igual que CP-273 | Presiones cortas de cada dirección con `client/probar_control.py` | Del botón leído en la PC a la posición nueva devuelta por el servidor pasan menos de 500 ms en todas las presiones (más 40 ms de margen por antirrebote, USB y dibujo) | OK | A | Manual con la placa, 17/11/2026 (procedimiento abajo) |
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
| CP-285 | Desconectar el cable en plena partida | Igual que CP-273, personaje moviéndose | Desconectar el cable USB y volver a conectarlo | Al desconectar: aviso naranja fijo y el personaje se detiene (no queda un botón pegado); se puede seguir con el teclado. Al reconectar: aviso verde y los botones vuelven a responder sin reiniciar el juego | OK | A | Manual con la placa, 17/11/2026 (procedimiento abajo) |

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
| CP-301 | Extraer con el botón físico de acción | Igual que CP-273; la arena dibuja el reactor (arena visual) y el HUD muestra el puntaje (US-24, listo el 19/11) | 1) Quedarse 5 s sobre el reactor sin presionar. 2) Presionar el botón de acción (D6). 3) Presionar lejos del reactor | 1) El puntaje no cambia. 2) Suma 10 y la barra del reactor baja. 3) No suma | **Pendiente** | A | Manual (procedimiento abajo) |

Además, por WebSocket con dos jugadores: la acción junto al reactor le suma 10 a quien la hizo, el
otro jugador lo ve y el reactor queda por debajo de su capacidad
(`s/test_movimiento_ws.py::test_la_accion_junto_al_reactor_suma_puntos_y_todos_lo_ven`). Se cuenta
dentro de CP-296 y CP-298 porque comprueba lo mismo de punta a punta.

## US-27 Logros

**Qué se comprueba:** al terminar una partida, cada jugador gana los logros cuya condición cumplió;
los logros quedan guardados en la base, no se repiten y el jugador puede consultarlos. Los retos con
puntos extra y mostrar los logros en el historial no están hechos (ver
[Fuera de estos casos](#fuera-de-estos-casos)).

**Cómo está hecho:** `EvaluadorLogros` es un suscriptor del motor de la partida (Observer, ADR 0006).
Junta la energía que cada jugador saca del reactor (evento `accion_realizada`) y las veces que lo
alcanza un guardián (`jugador_penalizado`, US-15). Lo de antes de iniciar la partida no cuenta: al
llegar `partida_iniciada` (US-17) borra lo juntado, igual que el motor pone los puntajes en cero.
Al recibir `partida_finalizada` guarda los logros nuevos en la tabla `logros_jugador`. El catálogo está en
`server/app/realtime/logros.py`:

| Clave | Nombre | Condición |
| --- | --- | --- |
| `primera_partida` | Bautizo nuclear | Terminar una partida |
| `primera_victoria` | Primera victoria | Ganar una partida (con empate no gana nadie) |
| `energia_300` | Sobrecarga | Extraer 300 de energía del reactor en una sola partida |
| `intocable` | Intocable | Terminar una partida con puntos sin que te alcance ningún guardián |

Desde el 19/11 el motor emite `partida_iniciada` y `partida_finalizada` (US-17). La mayoría de las
pruebas emiten los eventos a mano con el contrato de `server/app/realtime/eventos.py`
(`puntajes` {jugador_id: puntaje final} y `ganador_id`, `None` si hay empate); CP-318 usa el motor
real de punta a punta. La ceremonia de victoria (US-18) muestra los logros ganados en la partida.

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-302 | El catálogo no repite claves y trae los ejemplos de la historia | — | Catálogo de logros | Claves únicas; están `primera_victoria` y `energia_300` | OK | U | `s/test_logros.py::test_las_claves_del_catalogo_no_se_repiten`, `s/test_logros.py::test_el_catalogo_trae_los_ejemplos_de_la_historia` |
| CP-303 | No se vuelve a dar un logro que ya se tiene | El jugador ya tiene `primera_victoria` | Gana otra partida y saca 300 de energía | Solo es nuevo `energia_300` | OK | U | `s/test_logros.py::test_nuevos_logros_no_repite_los_que_ya_tenia` |
| CP-304 | La energía cuenta desde el límite exacto | — | 300 y 299 de energía del reactor | Con 300 gana `energia_300`; con 299 no | OK | U | `s/test_logros.py::test_la_energia_cuenta_desde_el_limite_exacto` |
| CP-305 | Al terminar la partida se guardan los logros de cada jugador | Ana y Beto en la partida, sin logros | Ana extrae 30 veces 10; fin con ganadora Ana (300 a 40), sin guardianes | Ana: `primera_partida`, `primera_victoria`, `energia_300` e `intocable`; Beto: `primera_partida` e `intocable` | OK | I | `s/test_logros.py::test_al_terminar_guarda_los_logros_de_cada_jugador` |
| CP-306 | Solo cuenta la energía del reactor y solo se guarda al terminar | Ana en la partida | 40 acciones de otro tipo (`terminal`); un `estado_actualizado` sin fin de partida | La energía del reactor de Ana queda en 0 y no gana `energia_300`; sin `partida_finalizada` no se guarda nada | OK | I | `s/test_logros.py::test_solo_cuenta_la_energia_del_reactor`, `s/test_logros.py::test_ignora_los_eventos_que_no_le_interesan` |
| CP-307 | Con empate nadie gana la primera victoria | Ana y Beto en la partida | Fin con 50 a 50 y `ganador_id` `None` | Ninguno de los dos gana `primera_victoria` | OK | I | `s/test_logros.py::test_con_empate_nadie_gana_la_primera_victoria` |
| CP-308 | Los logros no se duplican de una partida a otra | Ana termina una partida | Ana termina la primera con 0 puntos; juega y gana una segunda partida | Ana tiene `primera_partida` (de la primera), `primera_victoria` e `intocable` (de la segunda), una vez cada uno y con la partida en que los ganó | OK | I | `s/test_logros.py::test_no_duplica_logros_de_una_partida_a_otra` |
| CP-309 | El fin de partida se procesa una sola vez y acepta ids como texto | Ana en la partida | 1) El evento de fin llega dos veces con datos distintos. 2) Puntajes y ganador con ids como texto (como llegan desde JSON) | 1) Se guarda solo lo de la primera vez. 2) Ana gana `primera_victoria` igual | OK | I | `s/test_logros.py::test_una_partida_se_evalua_una_sola_vez`, `s/test_logros.py::test_acepta_ids_como_texto` |
| CP-310 | Cada partida nueva queda con los logros suscritos | `GestorMotores` con la base de la prueba | Se crea el motor de una partida y emite el fin de partida | Se guardan los logros sin cambiar nada más (Observer, abierto/cerrado) | OK | I | `s/test_logros.py::test_el_gestor_suscribe_los_logros_a_cada_partida` |
| CP-311 | Solo el jugador autenticado ve sus logros | Ana tiene `primera_victoria`; Beto no | `GET /logros` sin token y con el token de Beto | Sin token: 401. Beto ve `primera_victoria` como no obtenido | OK | I | `s/test_logros.py::test_sin_sesion_no_se_ven_los_logros`, `s/test_logros.py::test_cada_jugador_ve_solo_sus_logros` |
| CP-312 | El jugador ve todo el catálogo y cuáles ya ganó | Ana tiene `primera_partida` de una partida | `GET /logros` con el token de Ana | 200 con todo el catálogo; `primera_partida` con `obtenido` true y la partida; `primera_victoria` con `obtenido` false y `obtenido_en` null | OK | I | `s/test_logros.py::test_muestra_el_catalogo_con_los_obtenidos` |
| CP-313 | La migración crea la tabla `logros_jugador` | PostgreSQL 16 con la base en la migración anterior (`b124d9b1c989`) | `alembic upgrade head`, `downgrade -1`, `upgrade head` y `alembic check` | La tabla se crea con la restricción única `uq_logro_por_jugador` (jugador y logro); baja y sube sin errores; `check` sin diferencias con los modelos | OK | I, CI | CI (paso "Migraciones (alembic)" en cada PR); bajar, volver a subir y `check`, a mano el 16/11/2026 |
| CP-314 | Logros al terminar una partida real | Backend local, dos cuentas verificadas, la base sin logros para esas cuentas; el motor ya termina la partida (US-17, desde el 19/11) | Jugar una partida completa; el jugador 1 saca 300 de energía del reactor después de iniciar y gana | En `logros_jugador`: jugador 1 con `primera_partida`, `primera_victoria` y `energia_300`; jugador 2 con `primera_partida`; `intocable` a quien terminó con puntos sin que lo alcanzara un guardián. La ceremonia muestra los mismos logros y `GET /logros` de cada uno coincide con la tabla | **Pendiente** | A | Manual en la demo (procedimiento abajo) |
| CP-315 | Lo de antes de iniciar la partida no cuenta para los logros | Ana en la partida, todavía `esperando` | 30 extracciones de práctica; se inicia la partida; 1 extracción más y fin | Su energía del reactor queda en 10 y no gana `energia_300`; si las 30 extracciones son después de iniciar, sí lo gana | OK | I | `s/test_logros.py::test_la_energia_de_antes_de_iniciar_no_cuenta`, `s/test_logros.py::test_la_energia_despues_de_iniciar_si_cuenta` |
| CP-316 | Intocable: terminar con puntos sin que te alcance un guardián | Ana y Beto en la partida | Un guardián alcanza a Beto; fin 40 a 30. Además, un jugador que termina con 0 puntos y sin penalizaciones | Ana gana `intocable`, Beto no; con 0 puntos tampoco se gana | OK | I | `s/test_logros.py::test_alcanzado_por_un_guardian_no_es_intocable`, `s/test_logros.py::test_sin_puntos_no_es_intocable` |
| CP-317 | Las penalizaciones de antes de iniciar no cuentan | Ana en la partida, `esperando` | Un guardián la alcanza antes de iniciar; se inicia; fin con 20 puntos | Ana gana `intocable` | OK | I | `s/test_logros.py::test_las_penalizaciones_de_antes_de_iniciar_no_cuentan` |
| CP-318 | De punta a punta con el motor real | Motor con la jugadora sobre el reactor y el `EvaluadorLogros` suscrito | 3 extracciones de práctica; `iniciar_partida`; 1 extracción; `terminar` | Solo cuentan los 10 de energía de después de iniciar; se guardan `primera_partida`, `primera_victoria` e `intocable` | OK | I | `s/test_logros.py::test_con_el_motor_real_la_practica_no_cuenta_y_el_fin_guarda_logros` |

## US-27 Retos con puntos extra

**Criterio de aceptación (ERS, criterio 3 de la US-27):** el jugador puede completar retos durante
la partida que le dan puntos extra. Tres retos (`server/app/realtime/retos.py`, detalle en
`docs/logros-y-retos.md`): **Primera chispa** (+10, el primero en sacar energía del reactor
después de iniciar), **Racha nuclear** (+25, 50 de energía del reactor en 15 s) y **Sin rasguños**
(+30, 60 s seguidos sin que lo alcance un guardián). `GestorRetos` es otro suscriptor del motor
(Observer, ADR 0006).

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-319 | El catálogo trae los tres retos sin repetir | — | Catálogo de retos | `racha_nuclear`, `primera_chispa` y `sin_rasgunos`, todos con puntos mayores que 0 | OK | U | `s/test_retos.py::test_el_catalogo_trae_los_tres_retos_sin_repetir` |
| CP-320 | Antes de iniciar la partida no se cumple ningún reto | Partida `esperando` (práctica) | 6 extracciones en 2 s y 61 s sin golpes | Ningún reto, ningún punto extra y ningún `reto_completado` | OK | U | `s/test_retos.py::test_antes_de_iniciar_no_se_cumple_ningun_reto` |
| CP-321 | Primera chispa es solo para el primero | Partida iniciada con los jugadores 1 y 2 | El jugador 2 extrae en el segundo 1 y el 1 en el segundo 2 | Solo el jugador 2 cumple `primera_chispa` y suma 10 | OK | U | `s/test_retos.py::test_primera_chispa_es_solo_para_el_primero_que_extrae` |
| CP-322 | Racha nuclear: 50 de energía dentro de 15 s | Partida iniciada | 1) Extracciones en los segundos 0, 3, 6, 9 y 15. 2) En 0, 6, 9, 12 y 15,5 | 1) Con la cuarta (40) todavía no; con la quinta, justo a los 15 s, se cumple y suma 25. 2) No se cumple: la primera quedó fuera de la ventana | OK | U | `s/test_retos.py::test_racha_nuclear_con_50_de_energia_en_15_segundos`, `s/test_retos.py::test_racha_nuclear_no_cuenta_lo_que_quedo_fuera_de_los_15_segundos` |
| CP-323 | Sin rasguños: 60 s seguidos sin golpes | Partida iniciada | 1) Estados a los 59 y 60 s sin golpes. 2) Un guardián lo alcanza a los 30 s | 1) A los 59 s no; a los 60 s se cumple y suma 30. 2) La cuenta vuelve a empezar: a los 60 s no, a los 90 s sí | OK | U | `s/test_retos.py::test_sin_rasgunos_a_los_60_segundos_sin_golpes`, `s/test_retos.py::test_un_golpe_de_guardian_reinicia_la_cuenta_de_sin_rasgunos` |
| CP-324 | Cada reto se cumple una sola vez por partida | Partida iniciada | 200 de energía en 10 s y estados a los 60, 61 y 120 s | Suma 10 + 25 + 30 una sola vez; se publican los tres retos en orden | OK | U | `s/test_retos.py::test_cada_reto_se_cumple_una_sola_vez_por_partida` |
| CP-325 | Al cumplirse se avisa con sus datos | Partida iniciada con el jugador 7 | El jugador 7 extrae | Evento `reto_completado` con `jugador_id` 7, `reto`, `nombre` y `puntos` 10 | OK | U | `s/test_retos.py::test_publica_reto_completado_con_sus_datos` |
| CP-326 | Después del fin no hay retos y una partida nueva empieza de cero | 1) Partida finalizada. 2) Jugador con `primera_chispa` | 1) Extracción y 120 s sin golpes. 2) Llega otro `partida_iniciada` | 1) No suma nada. 2) Los retos cumplidos se olvidan | OK | U | `s/test_retos.py::test_terminada_la_partida_ya_no_se_cumplen_retos`, `s/test_retos.py::test_al_iniciar_otra_vez_se_olvida_lo_anterior` |
| CP-327 | Con el motor real los puntos se suman en la partida y cuentan para ganar | Motor con la jugadora sobre el reactor y `GestorRetos` suscrito | 1) 3 extracciones de práctica, iniciar, 5 extracciones y 60 s. 2) Meta de 20 puntos y 1 extracción | 1) Puntaje 50 + 10 + 25 y después + 30; la práctica no cuenta. 2) 10 de energía + 10 de Primera chispa terminan la partida con motivo `puntaje` | OK | I | `s/test_retos.py::test_con_el_motor_real_los_retos_suman_puntos_en_la_partida`, `s/test_retos.py::test_los_puntos_de_los_retos_cuentan_para_ganar` |
| CP-328 | Cada partida tiene los retos y quedan guardados | `GestorMotores`; base de la prueba con Ana y una partida | 1) Crear el motor de una partida. 2) Llega un `reto_completado` de Ana | 1) El motor tiene un `GestorRetos` suscrito. 2) Queda una fila en `eventos` con el tipo, Ana y los datos del reto | OK | I | `s/test_retos.py::test_el_gestor_suscribe_los_retos_a_cada_partida`, `s/test_retos.py::test_los_retos_cumplidos_quedan_en_la_tabla_eventos` |
| CP-329 | Retos en una partida real | Nube; dos cuentas en la misma partida; partida iniciada | El jugador 1 es el primero en extraer y hace 5 extracciones seguidas; el jugador 2 se aleja de los guardianes 60 s | El jugador 1 suma +10 y +25 en el HUD y el jugador 2 +30; cada reto aparece una vez como `reto_completado` en la tabla `eventos` | **Pendiente** | A | Manual en la demo (procedimiento abajo) |

**Mostrar los logros:** la ceremonia (US-18) los muestra al terminar; sus casos son del rol A. En
el historial (US-20) todavía no; mientras tanto se consultan con `GET /logros`.

## Apoyo a otras historias (hecho por el rol C)

### US-29 Efectos visuales: sprites y partículas de impacto

Los personajes, las barreras y los guardianes se dibujan con los sprites de `client/assets/sprites/`.
Cuando un guardián alcanza a un jugador salen chispas y una onda en ese punto (Flyweight, ADR 0012).

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-330 | Cada jugador se ve con su personaje y el color de su número | Sprites de los 4 personajes | Jugadores con número 1 a 4, y uno sin número o con un número raro | Personaje y aro de su color (rojo, verde, naranja y magenta); sin número usa el primero; el personaje cabe en el aro; la etiqueta va arriba | OK | U | `c/test_dibujo_jugadores.py::test_cada_numero_tiene_su_personaje_y_su_color`, `::test_dibuja_el_aro_del_color_de_su_numero_y_el_personaje_adentro`, `::test_sin_numero_o_con_uno_raro_usa_el_primero`, `::test_el_personaje_cabe_dentro_del_aro`, `::test_la_etiqueta_va_arriba_del_jugador` |
| CP-331 | Se ve el estado del jugador | — | Jugador `aturdido` y jugador `escudado` | Aturdido: personaje y aro grises. Escudado: aro azul y más grueso | OK | U | `c/test_dibujo_jugadores.py::test_aturdido_se_ve_gris`, `::test_escudado_tiene_el_aro_azul_y_mas_grueso` |
| CP-332 | Barreras con el sprite del muro y guardianes con el tanque morado | Sprites `muro.png` y `guardian.png` | Barrera fija, barrera móvil y guardián | Barreras rellenas de muro en cuadros de 30 sin salirse del rectángulo (la móvil con su borde); guardián teñido de morado dentro de su aro | OK | U | `c/test_dibujo_obstaculos.py::test_la_barrera_se_rellena_con_el_sprite_del_muro_en_cuadros_de_30`, `::test_el_muro_no_se_sale_del_rectangulo`, `::test_la_barrera_movil_lleva_el_muro_y_su_borde`, `c/test_dibujo_guardianes.py::test_el_guardian_es_el_tanque_morado_dentro_de_su_aro`, `::test_el_sprite_del_guardian_esta_tenido_de_morado` |
| CP-333 | Si falta una imagen se dibuja la figura de antes | Sin la carpeta de sprites | Dibujar jugador, barrera y guardián | Círculo del jugador, rectángulo gris de la barrera y círculo morado del guardián | OK | U | `c/test_dibujo_jugadores.py::test_si_falta_la_imagen_dibuja_el_circulo_de_antes`, `::test_una_imagen_que_no_existe_devuelve_none`, `c/test_dibujo_obstaculos.py::test_la_barrera_es_gris`, `c/test_dibujo_guardianes.py::test_el_guardian_es_un_circulo_morado_con_borde_oscuro` |
| CP-334 | Muchas partículas comparten pocos tipos (Flyweight) | — | Pedir el mismo tipo dos veces; varios impactos | La fábrica devuelve el mismo objeto; cientos de partículas usan solo 5 tipos | OK | U | `c/test_particulas.py::test_la_fabrica_reutiliza_el_mismo_tipo_para_los_mismos_datos`, `::test_muchas_particulas_comparten_pocos_tipos` |
| CP-335 | Un impacto lanza chispas que se apagan | — | `impacto(x, y)` y avanzar el tiempo | Chispas en todas las direcciones cerca del impacto; sin tiempo no se mueven; la onda dura 0,3 s y las chispas menos de 1 s | OK | U | `c/test_particulas.py::test_el_impacto_lanza_chispas_en_todas_direcciones`, `::test_dibuja_cerca_del_impacto`, `::test_sin_tiempo_no_se_mueven`, `::test_la_onda_dura_poco`, `::test_las_chispas_se_desvanecen_y_desaparecen` |
| CP-336 | Salen chispas cuando un guardián alcanza al jugador, una vez por golpe | Arena con un jugador | El servidor manda al jugador `normal` y después `aturdido`; sigue aturdido; se recupera y lo vuelven a alcanzar; otro llega ya aturdido | Chispas al pasar a aturdido, no mientras sigue aturdido, otra vez en el segundo golpe y nunca para quien llegó aturdido; se borran al salir de la arena | OK | I | `c/test_particulas.py::test_cuando_un_guardian_alcanza_al_jugador_salen_chispas`, `::test_seguir_aturdido_no_lanza_mas_chispas`, `::test_otro_golpe_despues_de_recuperarse_vuelve_a_lanzar_chispas`, `::test_un_jugador_que_llega_ya_aturdido_no_lanza_chispas`, `::test_las_chispas_se_mueven_con_el_reloj_de_la_arena_y_se_borran_al_salir` |

### US-17 Iniciar la partida con el mínimo de jugadores

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-337 | Con un solo jugador el botón está en gris y no inicia | El creador en el lobby, solo él conectado | Tocar el botón | Dice "Esperando jugadores (1/2)", en gris, y no llama al servidor | OK | I | `c/test_inicio_partida.py::test_con_un_solo_jugador_el_boton_sale_en_gris_y_no_inicia` |
| CP-338 | Al unirse el segundo el botón se activa | El creador solo en el lobby | Se conecta un segundo jugador; el mismo jugador aparece conectado dos veces | Con el segundo pasa a "Iniciar partida" en azul; el mismo jugador dos veces cuenta como uno | OK | I | `c/test_inicio_partida.py::test_cuando_se_une_el_segundo_el_boton_se_activa`, `::test_un_jugador_conectado_dos_veces_cuenta_una_sola_vez` |

### Escribir desde el celular (registro e inicio de sesión, RNF-07)

El canvas de pygame no abre el teclado del teléfono. En pantallas táctiles, tocar un campo de texto
abre el cuadro de texto del navegador (`client/src/navegador.py`).

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-339 | En el celular, tocar el campo pide el texto | Navegador de celular simulado | Tocar el campo de usuario y escribir `francisco`; tocarlo otra vez y cancelar | El campo queda con `francisco`; al cancelar queda como estaba | OK | U | `c/test_teclado_celular.py::test_en_el_celular_tocar_el_campo_pide_el_texto`, `::test_si_se_cancela_el_campo_queda_como_estaba` |
| CP-340 | La contraseña anterior no se muestra y se respeta el largo | Navegador de celular simulado | Campo de contraseña con texto; texto con salto de línea y más de 120 caracteres | El cuadro no muestra la contraseña anterior; se quitan los saltos de línea y se corta en 120 | OK | U | `c/test_teclado_celular.py::test_la_contrasena_no_se_muestra_en_el_cuadro`, `::test_respeta_el_largo_maximo_y_quita_saltos_de_linea` |
| CP-341 | En la compu se escribe como siempre | Escritorio, o navegador de compu simulado | Tocar el campo; tocar fuera del campo | No se abre ningún cuadro; el campo se activa para escribir con el teclado | OK | U | `c/test_teclado_celular.py::test_en_escritorio_no_se_abre_ningun_cuadro`, `::test_en_un_navegador_de_compu_se_escribe_con_el_teclado_normal`, `::test_tocar_fuera_del_campo_no_pide_nada` |
| CP-342 | Las pantallas cargan en el navegador sin librerías de escritorio | — | Importar el lobby, la búsqueda de partidas y el canal (con los campos de texto) | No se importa `websockets`, `requests` ni `serial` | OK | U | `c/test_canal_partida.py::test_cargar_las_pantallas_no_importa_librerias_de_escritorio` (regresión) |
| CP-343 | Registro e inicio de sesión desde un celular real | Nube; celular Android o iPhone | Abrir el dominio, crear una cuenta escribiendo en los campos e iniciar sesión | Sale el teclado del teléfono en cada campo; la cuenta se crea y se entra al lobby | **Pendiente** | A | Manual en la demo |

### US-04 Publicar el login con Google

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-344 | La política de privacidad está publicada en el dominio | PR #71 desplegado | Abrir `https://control-reactor.northcentralus.cloudapp.azure.com/privacidad.html` en la compu y en el celular | Carga la página con los datos que se guardan y cómo pedir que se borren | OK (24/11/2026) | A | Manual |
| CP-345 | Entra con Google una cuenta que no es de prueba | App en "Producción" en Google Auth Platform | En la nube, "Entrar con Google" con una cuenta que no está en la lista de usuarios de prueba | Entra al lobby; si es nueva, se crea su cuenta | **Pendiente** | A | Manual en la demo |

## Cómo ejecutar los casos de aceptación

1. Cargar el firmware (`hardware/firmware/control_reactor/control_reactor.ino`) en el Arduino Uno y
   cerrar el Monitor Serie del Arduino IDE (si queda abierto, ocupa el puerto).
2. En la raíz del repo: `docker compose up` y esperar `Application startup complete`.
3. En `client/`: `$env:CONTROL_PUERTO="COM5"` y `python main.py` (o `.\jugar.ps1 -Puerto COM5`).
4. Iniciar sesión, crear una partida y entrar a la arena.

**CP-274 (latencia), como se ejecutó el 17/11/2026:** con el backend local y la placa en COM5,
correr `python probar_control.py` en `client/` (cliente sin ventana que usa el mismo `EntradaSerial`
del juego), presionar cada dirección unas 10 veces con toques cortos y terminar con Ctrl+C. El
resumen da promedio, mediana, p95 y máximo, y guarda las mediciones en `latencia_<fecha>.csv`.
Todas las presiones quedaron por debajo de 500 ms.

Alternativa para medir la cadena completa (incluye el dibujo en pantalla): grabar con el celular en cámara lenta (o a 60 fps) la mano en el control y la
pantalla en el mismo encuadre. Presionar un botón de dirección 10 veces. En el video, contar los
cuadros entre el momento en que se hunde el botón y el primer cuadro en que el personaje se mueve, y
convertir a milisegundos (a 60 fps, 1 cuadro ≈ 16,7 ms; a 240 fps, ≈ 4,2 ms). Anotar el promedio y el
máximo; el caso pasa si el máximo es menor que 500 ms.

**CP-285 (desconexión), OK el 17/11/2026 con `probar_control.py` y con el juego:** con el personaje moviéndose (botón presionado), desconectar el cable USB.
Revisar el aviso naranja, que el personaje se detenga y que el teclado siga funcionando. Volver a
conectar el cable y esperar unos segundos: aviso verde y los botones responden otra vez.

**CP-301 (extracción):** en la arena, caminar hasta tocar el reactor y seguir el orden de la columna
Entrada. Revisar el puntaje del jugador en la tabla del HUD (US-24, lista el 19/11) y la energía del
reactor. El 17/11/2026 la extracción con el botón físico funcionó en el servidor (con
`probar_control.py`: +10 tocando el reactor, +0 lejos); falta que la arena dibuje el reactor para
verlo en el juego.

**En la nube (demo interna y defensa):** los celulares abren
`https://control-reactor.northcentralus.cloudapp.azure.com`; las computadoras corren
`.\jugar.ps1 -Nube` en `client/` (con `-SinControl` si no tienen el Arduino). Para ver las tablas:
`ssh reactor@control-reactor.northcentralus.cloudapp.azure.com`, `cd ~/reactor` y
`docker compose -f docker-compose.prod.yml exec db psql -U reactor -d reactor`.

**CP-329 (retos):** con la partida iniciada, el jugador 1 camina al reactor y es el primero en
extraer (+10, Primera chispa); después extrae 5 veces seguidas (+25, Racha nuclear). El jugador 2 se
mantiene lejos de los guardianes 60 s (+30, Sin rasguños). Revisar los puntajes en el HUD y en psql:
`SELECT jugador_id, datos FROM eventos WHERE tipo = 'reto_completado' ORDER BY id DESC;`.

**CP-314 (logros en una partida real):** con `docker compose up` en la raíz, entrar con dos cuentas
(una con el control y otra con el teclado) a la misma partida, iniciarla y jugarla hasta el final. Después, en
otra terminal: `docker compose exec db psql -U reactor -d reactor -c "SELECT jugador_id, logro,
partida_id FROM logros_jugador ORDER BY jugador_id;"` y comparar con `GET /logros` de cada jugador
(en `http://localhost:8000/docs`, con el token de esa cuenta). Sirve también para la parte de la
defensa en que se muestra cómo cambian las tablas.

Evidencia: captura o video de cada caso en la Wiki, página "Casos de prueba" del Sprint 3.

## Regresión

Las pruebas automáticas que cubren el control y el movimiento desde el Sprint 2 (CP-137 a CP-154 y
los casos de movimiento de la US-25) se vuelven a ejecutar en cada Pull Request en el CI, junto con
las de este documento. Ejecución del 16/11/2026 sobre `develop` (`05d70da`, después de mergear el
PR #50): **263 pruebas del servidor, 193 del cliente y las del firmware pasan**, sin fallos.
Ejecución del 16/11/2026 sobre `develop` (`ca10ea7`, con la US-27 y el PR #49 ya mergeados):
**278 pruebas del servidor** (incluidas las 15 de `s/test_logros.py`) **y 193 del cliente pasan**.
Ejecución del 19/11/2026 sobre `develop` (`c92c0d2`, con el fin de partida, el HUD y la ceremonia
del rol A) más los cambios de logros de CP-315 a CP-318: **373 pruebas del servidor** en
PostgreSQL 16 **y 235 del cliente pasan**.

Ejecución del 24/11/2026 sobre `develop` (`277dc37`, con los retos, los escenarios, los sprites,
las partículas, el botón de iniciar y el teclado del celular): **536 pruebas del servidor** en
PostgreSQL 16 **y 338 del cliente pasan**.

Para repetirlas: `python -m pytest -q` dentro de `server/` y de `client/` (el cliente con
`SDL_VIDEODRIVER=dummy`), y el firmware con los comandos de `hardware/firmware/README.md`.
