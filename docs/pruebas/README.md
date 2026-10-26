# Casos de prueba del Sprint 2

Consolidado de los casos de prueba del MVP 1. Cada rol documentó los suyos y este archivo los
resume; el detalle de cada caso (objetivo, precondiciones, entrada, resultado esperado y la prueba
que lo comprueba) está en:

| Documento | Cubre | Casos |
| --- | --- | --- |
| [casos-rol-a.md](casos-rol-a.md) | US-01 a US-06 y canal con token (AB#91) | CP-01 a CP-46, CP-126 a CP-129 |
| [casos-rol-b.md](casos-rol-b.md) | US-07, US-08, US-21 y US-25 | CP-47 a CP-125, CP-160 a CP-164 |
| [casos-rol-c.md](casos-rol-c.md) | Infraestructura, CI, firmware, simulador, red del cliente y versión móvil | CP-130 a CP-159 |

## Cómo se prueba

| Nivel | Qué cubre | Herramienta | Dónde corre |
| --- | --- | --- | --- |
| Unitarias | Una pieza sola, sin base de datos ni red: servicios, fábrica, motor, entradas, protocolo Serial, firmware | pytest; g++ para el firmware | En la PC y en el CI |
| Integración | Varias piezas juntas: API con base de datos, canal WebSocket con el motor, red del cliente con un servidor real | pytest con `TestClient` de FastAPI y PostgreSQL 16 | En el CI, con una base de datos temporal |
| Aceptación | El juego o el hardware completo, a mano | Juego, Tinkercad, celular | A mano, con el resultado anotado en el caso |

Todo lo automático corre en cada Pull Request (`.github/workflows/ci.yml`): lint con ruff,
migraciones, pruebas del backend contra PostgreSQL, pruebas del cliente, compilación del firmware
para Arduino Uno y sus pruebas en la PC, y el build de la imagen Docker. Un PR no se puede mergear
a `develop` si algún job falla.

## Resumen

| Historia o área | Casos | OK | Pendiente |
| --- | --- | --- | --- |
| US-01 Registro de usuario | 7 | 7 | 0 |
| US-02 Verificación de correo | 9 | 9 | 0 |
| US-03 Inicio de sesión | 7 | 7 | 0 |
| US-04 Inicio de sesión con Google | 8 | 8 | 0 |
| US-05 Recuperación de contraseña | 8 | 8 | 0 |
| US-06 Edición del perfil | 7 | 7 | 0 |
| Canal con token (AB#91) | 4 | 4 | 0 |
| US-07 Creación de partida | 12 | 12 | 0 |
| US-08 Unirse a una partida | 27 | 27 | 0 |
| US-21 Guardado persistente de datos | 10 | 10 | 0 |
| US-25 Movimiento por el mapa | 35 | 35 | 0 |
| CI y contenedores | 7 | 7 | 0 |
| Firmware del control | 6 | 6 | 0 |
| Lectura del control en el cliente | 12 | 12 | 0 |
| Red del cliente y versión móvil | 5 | 5 | 0 |
| **Total** | **164** | **164** | **0** |

Por tipo (roles B y C, que lo indican caso por caso): 49 unitarios, 57 de integración y 8 de
aceptación (un caso cuenta en dos tipos y otro es el lint del CI). Los 50 casos del rol A están automatizados con
pytest (unitarios y de integración).

## Resultado de la ejecución

- **Pruebas automáticas:** 192 del servidor y 167 del cliente, todas pasan, más las pruebas del
  firmware con 5 botones y con joystick.
- **CI de `develop`:** los 4 jobs en verde en el commit `dd5c276` (25/10/2026), con la pantalla de
  la arena y los ADRs de patrones ya integrados.
- **Docker (CP-95 y CP-131, 23/10/2026):** con una base nueva el contenedor aplicó las 6 migraciones
  solo, `/health/db` respondió y la partida creada siguió disponible después de
  `docker compose restart server` y de `docker compose down` + `up` (capturas en `evidencias/`).
- **Para repetirlas:** `pytest` dentro de `server/` y de `client/`; el firmware se prueba con los
  comandos de `hardware/firmware/README.md`.

## Pendientes

Ninguno: los 164 casos están en OK. El CP-125 (ver el movimiento en pantalla) se cerró con la
pantalla de la arena (task 39), y los casos de la arena se numeraron CP-160 a CP-164 para no repetir
los identificadores de los roles A y C.
