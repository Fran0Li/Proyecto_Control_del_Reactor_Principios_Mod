# Manual técnico — Control del Reactor

> También en la Wiki del proyecto: sección Manuales.

**Para quién es:** quien tenga que instalar, correr, probar, desplegar o mantener Control del Reactor. Resume lo que está en el repositorio y enlaza los documentos con el detalle.

**Repositorio:** https://github.com/Fran0Li/Proyecto_Control_del_Reactor_Principios_Mod (rama de trabajo `develop`, versión entregada en `main`).

## 1. Arquitectura en una página

| Pieza | Tecnología | Dónde |
| --- | --- | --- |
| Cliente de escritorio | Python 3.12 con pygame-ce 2.5.8 | `client/` |
| Cliente web y móvil | El mismo cliente compilado a WebAssembly con pygbag 0.9.3 ([ADR 0002](https://dev.azure.com/proyecto-control-del-reactor/Control%20del%20Reactor/_wiki/wikis/Control-del-Reactor.wiki?pagePath=/Decisiones%20t%C3%A9cnicas/ADR%200002%20Cliente%20m%C3%B3vil%20con%20pygbag)) | `client/`, imagen `deploy/web.Dockerfile` |
| Backend | FastAPI: API REST y WebSocket de la partida; servidor autoritativo (el motor corre en el servidor a 20 ciclos por segundo) | `server/app/` |
| Base de datos | PostgreSQL 16 con SQLAlchemy y migraciones Alembic | `server/app/models/`, `server/alembic/` |
| Control físico | Arduino Uno con 5 botones, por USB (Serial) a la compu del jugador | `hardware/firmware/` |
| Contenedores | Docker y Docker Compose (desarrollo y producción) | `docker-compose.yml`, `docker-compose.prod.yml` |
| Nube | VM de Azure con Caddy (HTTPS automático) | `deploy/`, [ADR 0010](https://dev.azure.com/proyecto-control-del-reactor/Control%20del%20Reactor/_wiki/wikis/Control-del-Reactor.wiki?pagePath=/Decisiones%20t%C3%A9cnicas/ADR%200010%20Despliegue%20en%20la%20nube) |
| CI/CD | GitHub Actions: CI en cada PR y despliegue automático desde `develop` | `.github/workflows/` |

El backend va por capas: `api/routes` (endpoints) → `services` (lógica) → `repositories` (acceso a datos, patrón Repository) → `models`. El tiempo real está en `realtime/` (motor de partida, gestor de motores, eventos especiales).

Vistas y diagramas: [Arquitectura Sprint 2](https://dev.azure.com/proyecto-control-del-reactor/Control%20del%20Reactor/_wiki/wikis/Control-del-Reactor.wiki?pagePath=/Arquitectura%20Sprint%202) y [Arquitectura Sprint 3](https://dev.azure.com/proyecto-control-del-reactor/Control%20del%20Reactor/_wiki/wikis/Control-del-Reactor.wiki?pagePath=/Arquitectura%20Sprint%203). Patrones y decisiones: [Decisiones técnicas](https://dev.azure.com/proyecto-control-del-reactor/Control%20del%20Reactor/_wiki/wikis/Control-del-Reactor.wiki?pagePath=/Decisiones%20t%C3%A9cnicas).

## 2. Requisitos

- **Para el backend:** Docker Desktop.
- **Para el cliente de escritorio:** Python 3.12 (Windows, Linux o Mac).
- **Para el control:** Arduino Uno con el firmware cargado y el Arduino IDE (solo para cargarlo).
- **Para desplegar:** cuenta de Azure (se usó Azure for Students) y acceso al repositorio de GitHub.

## 3. Correr todo en local

### Backend y base de datos

```bash
cp .env.example .env        # en Windows: copy .env.example .env
docker compose up --build
```

- API: http://localhost:8000 · documentación interactiva: http://localhost:8000/docs
- Estado: http://localhost:8000/health y http://localhost:8000/health/db

Al arrancar, el contenedor del servidor aplica las migraciones pendientes (`alembic upgrade head`) y cierra las partidas que quedaron activas de una ejecución anterior. Los datos viven en el volumen `pgdata`: sobreviven a `docker compose down`; solo `docker compose down -v` los borra.

### Cliente de escritorio (Windows)

```powershell
cd client
.\jugar.ps1                 # control en COM5, backend local
.\jugar.ps1 -Puerto COM3    # si Windows le asignó otro puerto a la placa
.\jugar.ps1 -Simulador      # sin la placa, con hardware/simulator
.\jugar.ps1 -SinControl     # solo teclado
.\jugar.ps1 -Nube           # contra el juego desplegado en Azure
```

El script instala lo que falte, configura el puerto del control y avisa si el backend no responde. Si PowerShell no deja correrlo: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`.

A mano (o en Linux y Mac): `pip install -r requirements.txt` y `python main.py` dentro de `client/`. Variables útiles: `SERVER_URL` (otro servidor) y `CONTROL_PUERTO` (por ejemplo `COM3` o `socket://localhost:7777` para el simulador).

### Cliente en el navegador o el celular (red local)

```bash
cd client
pip install pygbag
pygbag --bind <IP de la compu> --port 8001 .
```

Abrir `http://<IP>:8001` en el celular, en la misma red WiFi. En local el login con Google no funciona desde el celular: se entra con usuario y contraseña.

## 4. Configuración (`.env`)

El archivo `.env` **nunca se sube al repositorio**; la plantilla es `.env.example` (local) y `deploy/.env.prod.example` (nube).

| Variable | Para qué |
| --- | --- |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL` | Conexión a PostgreSQL |
| `APP_ENV` | Entorno (`development` en local; otro valor en la nube) |
| `CORS_ORIGENES` | Orígenes web que pueden llamar a la API |
| `JWT_SECRET` | Clave para firmar los tokens de sesión (mínimo 32 caracteres, distinta en producción) |
| `URL_PUBLICA` | Dirección con la que se arman los enlaces de los correos |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Envío de correos (verificación y recuperación). Vacío: los correos se escriben en el log |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Login con Google ([docs/google-oauth.md](../google-oauth.md)) |

Para revisar la configuración del correo sin mostrar la contraseña, usar el comando de la sección 5 de [docs/despliegue.md](../despliegue.md).

## 5. Base de datos

| Tabla | Guarda |
| --- | --- |
| `usuarios` | Cuentas: usuario, correo, hash de la contraseña, verificación, Google, rol y bloqueo |
| `tokens_usuario` | Códigos de verificación de correo y de recuperación de contraseña |
| `partidas` | Estado (`esperando`, `en_curso`, `finalizada`), escenario, tiempo límite, meta y fechas |
| `participaciones` | Jugadores de cada partida, con puntaje y posición final |
| `eventos` | Lo que pasa en la partida (`partida_iniciada`, `accion_realizada`, `jugador_penalizado`, `reto_completado`, `evento_especial_iniciado`, `partida_finalizada`, etc.) |
| `ranking_global` | Puntos totales y victorias de cada jugador |
| `logros_jugador` | Logros obtenidos |

Entrar a la base: `docker compose exec db psql -U reactor -d reactor` (local) o el comando de la sección 8 (nube). Una migración nueva se crea con `alembic revision --autogenerate -m "..."` dentro del contenedor o del entorno del servidor, y se aplica sola al arrancar.

## 6. Pruebas

| Qué | Comando | Dónde corre |
| --- | --- | --- |
| Backend (unitarias e integración) | `cd server && pytest` | Local con SQLite; en el CI contra PostgreSQL 16 con `TEST_DATABASE_URL` |
| Cliente | `cd client && pytest` | Local y CI, sin ventana |
| Firmware | Compilación para Arduino Uno y pruebas del firmware en la PC | CI |
| Lint | `ruff check .` en `server/` y en `client/` | Local y CI |
| Aceptación | A mano con el juego, según los casos de prueba | [Casos de prueba Sprint 3](https://dev.azure.com/proyecto-control-del-reactor/Control%20del%20Reactor/_wiki/wikis/Control-del-Reactor.wiki?pagePath=/Casos%20de%20prueba%20Sprint%203) |

Para usar PostgreSQL en local: `TEST_DATABASE_URL=postgresql+psycopg://usuario:clave@localhost/base_de_pruebas pytest`. **Nunca** apuntarla a la base de desarrollo: las pruebas borran y crean tablas.

Para instalar exactamente las versiones del CI: `pip install -r requirements-dev.txt -c constraints.txt` ([docs/dependencias.md](../dependencias.md)).

## 7. Integración y entrega continua

**CI** (`.github/workflows/ci.yml`), en cada Pull Request y en cada push a `develop`. Son los 4 checks obligatorios para mergear:

1. Lint y pruebas del backend (ruff, migraciones con Alembic y pytest contra PostgreSQL 16).
2. Build de la imagen Docker.
3. Lint y pruebas del cliente.
4. Firmware del control (compilación para Arduino Uno y sus pruebas).

**CD** (`.github/workflows/deploy.yml`): cuando el CI pasa en `develop`, entra por SSH a la VM, deja el commit exacto, reconstruye y levanta los contenedores, y verifica que `/api/health/db` responda. Tarda menos de un minuto.

**Ramas:** una rama por historia (`feature/US-XX-...`, `fix/...`, `docs/...`), todo entra a `develop` por Pull Request con una aprobación y el CI en verde; `main` recibe las versiones entregadas con un tag por sprint. Detalle: [Estrategia de ramas](https://dev.azure.com/proyecto-control-del-reactor/Control%20del%20Reactor/_wiki/wikis/Control-del-Reactor.wiki?pagePath=/Estrategia%20de%20ramas%20y%20estructura%20del%20repositorio).

## 8. Nube (Azure)

| Dato | Valor |
| --- | --- |
| Juego | https://control-reactor.northcentralus.cloudapp.azure.com |
| API | https://control-reactor.northcentralus.cloudapp.azure.com/api |
| VM | `vm-reactor` (Ubuntu 24.04, Standard_B2ats_v2, northcentralus), grupo `rg-control-reactor` |
| Contenedores | `db` (PostgreSQL), `server` (FastAPI), `web` (Caddy con el cliente web y el proxy a `/api`) |

Operación (por SSH, `ssh reactor@control-reactor.northcentralus.cloudapp.azure.com`, dentro de `~/reactor`):

| Tarea | Comando |
| --- | --- |
| Ver los contenedores | `docker compose -f docker-compose.prod.yml ps` |
| Ver los logs del servidor | `docker compose -f docker-compose.prod.yml logs -f server` |
| Entrar a la base | `docker compose -f docker-compose.prod.yml exec db psql -U reactor -d reactor` |
| Desplegar a mano | `git pull && ./deploy/desplegar.sh` |
| Volver a una versión | `git reset --hard <commit> && ./deploy/desplegar.sh` |
| Crear el administrador | `docker compose -f docker-compose.prod.yml exec server python -m app.scripts.crear_admin --usuario admin --correo <correo>` (pide la contraseña) |
| Cerrar las partidas activas | `docker compose -f docker-compose.prod.yml exec server python -m app.scripts.cerrar_partidas_activas` |

No borrar los volúmenes `pgdata` (datos) ni `caddy_data` (certificados). Crear la VM desde cero, conectar el CD, el correo y apagar o borrar todo al terminar: [docs/despliegue.md](../despliegue.md). Más contexto en [Infraestructura y nube](https://dev.azure.com/proyecto-control-del-reactor/Control%20del%20Reactor/_wiki/wikis/Control-del-Reactor.wiki?pagePath=/Avances%20Sprint%203/Infraestructura%20y%20nube).

## 9. Control físico

- **Placa:** Arduino Uno, 5 botones en D2 a D6 con `INPUT_PULLUP` (arriba, abajo, izquierda, derecha y acción).
- **Protocolo:** Serial a 115200 baudios. La placa manda `HELLO` al arrancar, `BTN <UP|DOWN|LEFT|RIGHT|ACTION> <PRESS|RELEASE>` por cada botón y `HB` cada segundo. Si pasan 3 segundos sin `HB`, el cliente da el control por desconectado y avisa al jugador.
- **Camino:** el cliente de escritorio lee el puerto y traduce cada botón al mismo mensaje `entrada` del WebSocket que usa el teclado (patrón Adapter). Detalle: [Contrato de la API de hardware](https://dev.azure.com/proyecto-control-del-reactor/Control%20del%20Reactor/_wiki/wikis/Control-del-Reactor.wiki?pagePath=/Contrato%20de%20la%20API%20de%20hardware).
- **Cargar el firmware:** abrir `hardware/firmware/control_reactor` en el Arduino IDE y subirlo a la placa. Instrucciones: `hardware/firmware/README.md`.
- **Sin placa:** `hardware/simulator/` simula los botones por un socket (`.\jugar.ps1 -Simulador`).
- **Probar el control sin ventana:** `client/probar_control.py` (casos CP-274, CP-285 y CP-301).

El **Monitor Serie del Arduino IDE tiene que estar cerrado** mientras se juega: ocupa el puerto y el cliente no lo puede abrir.

## 10. Problemas comunes

| Síntoma | Causa probable | Qué hacer |
| --- | --- | --- |
| `jugar.ps1` dice que el backend no responde | Docker no está corriendo, o la VM está apagada (con `-Nube`) | `docker compose up`, o encender la VM en el portal de Azure |
| El control no mueve al personaje | Monitor Serie abierto, otro puerto COM o cable suelto | Cerrar el Arduino IDE; probar `-Puerto COM3`; revisar en el Administrador de dispositivos |
| "El jugador ya está en una partida activa" | Quedó abierta una partida de una prueba anterior | Esperar 60 s si nadie está conectado, o usar el script de cerrar partidas |
| No llegan los correos | `SMTP_*` vacío o mal escrito | Revisar con el comando de `docs/despliegue.md`; con SMTP vacío los correos salen en el log del servidor |
| El login con Google no abre o queda esperando | Faltan `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET`, o la URI de redirección no está en Google Cloud | Ver `docs/google-oauth.md` |
| Las pruebas del servidor fallan en local con PostgreSQL | `TEST_DATABASE_URL` apunta a una base con datos o sin permisos | Usar una base vacía solo para pruebas |
