# Casos de prueba del Sprint 2

Consolidado de los casos de prueba del MVP 1. Cada rol documentó los suyos y este archivo los
resume; el detalle de cada caso (objetivo, precondiciones, entrada, resultado esperado y la prueba
que lo comprueba) está en:

| Documento | Cubre | Casos |
| --- | --- | --- |
| [casos-rol-a.md](casos-rol-a.md) | US-01 a US-06 y canal con token (AB#91) | CP-01 a CP-46, CP-126 a CP-129 |
| [casos-rol-b.md](casos-rol-b.md) | US-07, US-08, US-21 y US-25 | CP-47 a CP-125 |
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
| US-21 Guardado persistente de datos | 10 | 9 | 1 |
| US-25 Movimiento por el mapa | 30 | 29 | 1 |
| CI y contenedores | 7 | 6 | 1 |
| Firmware del control | 6 | 6 | 0 |
| Lectura del control en el cliente | 12 | 12 | 0 |
| Red del cliente y versión móvil | 5 | 5 | 0 |
| **Total** | **159** | **156** | **3** |

Por tipo (roles B y C, que lo indican caso por caso): 44 unitarios, 57 de integración y 8 de
aceptación (un caso cuenta en dos tipos y otro es el lint del CI). Los 50 casos del rol A están automatizados con
pytest (unitarios y de integración).

## Resultado de la ejecución

- **Pruebas automáticas:** 192 del servidor y 149 del cliente, todas pasan, más las pruebas del
  firmware con 5 botones y con joystick.
- **CI de `develop`:** los 4 jobs en verde en el commit `8f78e6c` (22/10/2026),
  [ejecución en GitHub Actions](https://github.com/Fran0Li/Proyecto_Control_del_Reactor_Principios_Mod/actions/runs/39898321981).
- **Para repetirlas:** `pytest` dentro de `server/` y de `client/`; el firmware se prueba con los
  comandos de `hardware/firmware/README.md`.

## Pendientes

| Caso | Qué falta | Cómo se cierra |
| --- | --- | --- |
| CP-95 | Comprobar que los datos sobreviven a un reinicio | `docker compose up`, crear una cuenta y una partida, `docker compose restart server` y ver que siguen |
| CP-131 | Comprobar `/health/db` con Docker | En la misma sesión que CP-95, abrir `http://localhost:8000/health/db` |
| CP-125 | Ver el movimiento en pantalla | Depende de la pantalla de la arena (US-25, task 39) |
