# Casos de prueba — Rol C (infraestructura, hardware y cliente base)

Cubre el PBI #72 (Feature "Infraestructura y DevOps"): CI, Docker, base de datos, firmware del
control, simulador, lectura Serial en el cliente y la red del cliente para escritorio y navegador.
La numeración sigue a la de los roles A y B.

**Tipos:** **U** unitaria, **I** integración y **A** aceptación (a mano). **CI** indica que lo
comprueba un paso del pipeline de GitHub Actions en cada Pull Request.

Archivos: `s/` = `server/tests/`, `c/` = `client/tests/`, `fw/` = `hardware/firmware/pruebas/`.

## Integración continua y contenedores

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-130 | El servidor responde | Backend corriendo | `GET /health` | 200 `{"status": "ok"}` | OK | I | `s/test_health.py::test_health_responde_ok` |
| CP-131 | La base de datos responde | `docker compose up` | `GET /health/db` | 200 con `"database": "conectada"` | Pendiente | A | Manual, junto con CP-95 |
| CP-132 | El navegador puede llamar a la API | Cliente web en otro puerto | Preflight `OPTIONS` y `GET` con `Origin` | Respuestas con las cabeceras CORS | OK | I | `s/test_cors.py` |
| CP-133 | Las migraciones crean el esquema en PostgreSQL | Base vacía | `alembic upgrade head` | Termina sin errores | OK | I, CI | Paso "Migraciones (alembic)" del job del backend |
| CP-134 | Las pruebas del servidor corren contra PostgreSQL | PostgreSQL 16 temporal en el CI | `pytest` con `TEST_DATABASE_URL` | Todas pasan | OK | I, CI | Job "Lint y pruebas del backend" |
| CP-135 | La imagen del backend se construye | Pruebas del backend en verde | `docker build ./server` | Imagen creada | OK | I, CI | Job "Build de la imagen Docker" |
| CP-136 | El código cumple el estilo | — | `ruff check .` en `server/` y `client/` | Sin errores | OK | CI | Jobs del backend y del cliente |

## Firmware del control (Arduino Uno)

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-137 | El firmware compila para Arduino Uno | — | `control_reactor.ino` | Compila sin errores | OK | I, CI | Paso "Compilar para Arduino Uno" |
| CP-138 | Saludo y latidos | Arduino encendido | Arranque y 2,5 s sin tocar nada | `HELLO CR-PAD-01 1.0` y un `HB` por segundo | OK | U, CI | `fw/prueba_firmware.cpp` |
| CP-139 | Los 5 botones | Pines D2 a D6 con `INPUT_PULLUP` | Presionar y soltar cada botón | `BTN <botón> PRESS` y `BTN <botón> RELEASE` | OK | U, CI | `fw/prueba_firmware.cpp` (5 botones) |
| CP-140 | Antirrebote de 20 ms | — | El botón parpadea 5 ms antes de quedar presionado | Un solo `PRESS` | OK | U, CI | `fw/prueba_firmware.cpp` |
| CP-141 | Variante con joystick | `USAR_JOYSTICK 1` | Palanca, zona de histéresis, diagonal, ruido de 3 ms | Mismos mensajes `BTN`; la histéresis y el ruido no generan mensajes | OK | U, CI | `fw/prueba_firmware.cpp` con `-DUSAR_JOYSTICK=1` |
| CP-142 | Circuito armado | Tinkercad | Simular el circuito con el firmware | Cada botón envía su línea por el monitor Serial | OK | A | Circuito en Tinkercad (enlace en el PR #11) |

## Lectura del control en el cliente (Serial y simulador)

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-143 | Interpretar las líneas del contrato | — | Líneas válidas e inválidas | Las válidas se convierten en mensajes; las inválidas se descartan | OK | U | `c/test_protocolo_serial.py` |
| CP-144 | Conexión y botones | Puerto falso | `HELLO`, `BTN UP PRESS` y `BTN UP RELEASE` | Estado `conectado`, aviso `dispositivo` y las dos entradas de `arriba` | OK | U | `c/test_entrada_serial.py::test_saludo_conecta_y_botones_generan_entradas` |
| CP-145 | Línea partida en dos lecturas | Puerto falso | `BTN LE` y luego `FT PRESS` | Una sola entrada `izquierda` / `presionado` | OK | U | `c/test_entrada_serial.py::test_linea_partida_en_dos_lecturas` |
| CP-146 | Línea inválida | Puerto falso | `BTN JUMP PRESS` entre líneas válidas | Se descarta y se cuenta; las demás siguen | OK | U | `c/test_entrada_serial.py::test_linea_invalida_se_descarta_sin_afectar_las_demas` |
| CP-147 | Presionado repetido | Puerto falso | Dos `BTN UP PRESS` seguidos | Una sola entrada | OK | U | `c/test_entrada_serial.py::test_presionado_repetido_no_duplica` |
| CP-148 | Desconexión por falta de latidos | Botón presionado | 3 s sin mensajes | Suelta los controles y avisa `desconectado` | OK | U | `c/test_entrada_serial.py::test_sin_latidos_suelta_controles_y_avisa` |
| CP-149 | Los latidos mantienen la conexión | Conectado | `HB` cada segundo | Sigue `conectado` | OK | U | `c/test_entrada_serial.py::test_latidos_mantienen_la_conexion` |
| CP-150 | Cable desconectado | Conectado | Error al leer el puerto | Se desconecta y reintenta cada 2 s | OK | U | `c/test_entrada_serial.py::test_error_de_lectura_desconecta_y_reintenta_cada_2_s` |
| CP-151 | Puerto que no existe | — | `CONTROL_PUERTO` que no existe | El cliente sigue funcionando, queda `desconectado` y sin entradas | OK | U | `c/test_entrada_serial.py::test_puerto_que_no_existe_no_rompe_el_cliente` |
| CP-152 | El simulador se identifica | — | `socket://localhost:7777` | `origen` = `simulador` | OK | U | `c/test_entrada_serial.py::test_simulador_usa_origen_simulador` |
| CP-153 | Con pyserial real | pyserial instalado | Puerto `loop://` | Lee las líneas como desde el Arduino | OK | I | `c/test_entrada_serial.py::test_con_pyserial_real_por_loopback` |
| CP-154 | De punta a punta con el simulador | Servidor real, simulador por socket | `BTN DOWN PRESS` durante 1 s | El servidor recibe `dispositivo: conectado` y el jugador baja 120 px (la velocidad del motor) | OK | A | Ejecutado el 20/10/2026 contra el servidor de `develop` |

## Red del cliente y versión móvil (ADR 0002)

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-155 | HTTP desde el cliente de escritorio | Servidor de prueba local | `GET` y `POST` | Respuesta y JSON correctos | OK | I | `c/test_red_escritorio.py::test_get_y_post` |
| CP-156 | La ventana no se congela | Servidor que tarda en responder | Petición en curso | El ciclo del juego sigue corriendo | OK | I | `c/test_red_escritorio.py::test_no_congela_el_ciclo_mientras_espera` |
| CP-157 | Servidor caído | Sin servidor | Petición | `ErrorDeRed`, sin romper el cliente | OK | I | `c/test_red_escritorio.py::test_servidor_caido_lanza_error_de_red` |
| CP-158 | Versión móvil con pygbag | Prototipo servido con pygbag, celular en la misma red | Abrir la página, mover con los botones táctiles | Carga, se conecta por WebSocket, mueve al jugador y no quedan botones pegados; latencia de 33 ms | OK | A | Prueba técnica del 09/10/2026 (ADR 0002) |
| CP-159 | Teclado y táctil en el cliente real | — | Ver CP-121 a CP-124 | — | OK | U | `c/test_entradas_jugador.py` |

## Pendientes

- **CP-131** (base de datos con Docker): se prueba junto con CP-95 levantando `docker compose up`.
