# Guía del equipo — Sprint 2

Lean esto antes de empezar a programar. Explica qué trae el repo, cómo levantarlo y dónde trabaja cada uno.

**Enlaces**

- Repositorio: `<link del repo>`
- Azure Boards: https://dev.azure.com/proyecto-control-del-reactor/Control%20del%20Reactor/_workitems/recentlyupdated/
- Wiki: https://dev.azure.com/proyecto-control-del-reactor/Control%20del%20Reactor/_wiki/wikis/Control-del-Reactor.wiki/1/Control-del-Reactor-%C3%8Dndice
- Entrega del Sprint 2: **jueves 22 de octubre**

---

## 1. Qué leer primero

En este orden (son cortos):

1. `README.md`: qué hay en el repo y cómo levantarlo.
2. `docs/estrategia-de-ramas.md`: cómo trabajamos con ramas, commits y PRs. **Obligatorio.**
3. `docs/adr/0001-stack-tecnologico.md`: por qué usamos Python, FastAPI, PostgreSQL, etc.
4. Esta guía, sobre todo la sección de su rol.

---

## 2. Qué instalar

| Herramienta | Para qué |
| --- | --- |
| GitHub Desktop | Clonar, hacer commits, ramas y PRs |
| Docker Desktop | Levantar el backend y PostgreSQL |
| Python 3.12 | Correr pruebas y el cliente pygame en local |
| VS Code (u otro editor) | Programar |

---

## 3. Primeros pasos

1. **Aceptar la invitación** al repo que les llega al correo de GitHub.
2. **Clonar:** GitHub Desktop → *File → Clone repository* → elegir `control-del-reactor`.
3. **Crear su `.env`:** en la carpeta del repo, copiar `.env.example` y renombrar la copia a `.env`.
   En terminal de Windows: `copy .env.example .env`. Este archivo **no se sube** al repo.
4. **Levantar el backend:** con Docker Desktop abierto, en una terminal dentro de la carpeta del repo:

   ```bash
   docker compose up --build
   ```

   La primera vez tarda unos minutos. Para apagarlo: `Ctrl+C`.
5. **Verificar:** abrir http://localhost:8000/health/db en el navegador.
   Si dice `"database": "conectada"`, todo está bien.
6. **Probar el cliente** (opcional):

   ```bash
   cd client
   pip install -r requirements.txt
   python main.py
   ```

   Se abre una ventana que dice "Servidor: conectado".

La página http://localhost:8000/docs muestra todas las rutas del backend y permite probarlas sin el cliente. Úsenla mucho.

---

## 4. Qué trae el repo

```
control-del-reactor/
├── server/                 Backend (FastAPI)
│   ├── app/
│   │   ├── main.py         Punto de entrada: crea la app y registra las rutas
│   │   ├── api/routes/     Endpoints (URLs). Solo reciben la petición y llaman a un servicio
│   │   ├── services/       Lógica de negocio (validaciones, reglas)
│   │   ├── repositories/   Consultas a la base de datos (patrón Repository)
│   │   ├── models/         Tablas de la BD como clases (SQLAlchemy)
│   │   ├── realtime/       WebSocket de las partidas
│   │   ├── core/config.py  Lee la configuración del .env
│   │   └── db/session.py   Conexión a PostgreSQL
│   ├── tests/              Pruebas con pytest
│   ├── Dockerfile          Receta del contenedor del backend
│   ├── requirements.txt    Librerías del backend
│   └── requirements-dev.txt  + librerías de desarrollo (pytest, ruff)
├── client/                 Juego en pygame
│   ├── main.py             Arranca el juego
│   └── src/                Código del cliente (pantallas, red, arena…)
├── hardware/               Control físico (ESP32) y simulador
├── docs/                   ADRs, estrategia de ramas y esta guía
├── .github/workflows/      CI: lint, pruebas y build de Docker en cada PR
├── docker-compose.yml      Levanta backend + PostgreSQL juntos
└── .env.example            Plantilla de configuración
```

**Regla de capas del backend:** `routes → services → repositories → models`.
Un endpoint nunca consulta la BD directamente: llama a un servicio, y el servicio usa un repositorio.
Esto es lo que el profe evalúa como "separación por capas" y SOLID.

---

## 5. Dónde trabaja cada uno

### Luis — Rol A: Usuarios y autenticación (US-01 a US-06)

| Archivo a crear | Contenido |
| --- | --- |
| `server/app/api/routes/auth.py` | Registro, login, verificación, recuperación, Google |
| `server/app/api/routes/profile.py` | Ver y editar perfil |
| `server/app/services/auth_service.py` | Validaciones, hash de contraseña, JWT, tokens |
| `server/app/services/email_service.py` | Envío de correos |
| `server/app/repositories/user_repository.py` | Consultas de usuarios |
| `server/tests/test_auth.py` | Pruebas de auth |
| `client/src/screens/` | Pantallas de login, registro y perfil |

Registrar los routers nuevos en `server/app/main.py` (ya hay líneas comentadas de ejemplo).

### Julián — Rol B: Núcleo del juego y datos (US-07, US-08, US-21, US-25)

| Archivo a crear | Contenido |
| --- | --- |
| `server/app/models/` | Tablas: usuarios, partidas, participaciones, puntajes, eventos |
| `server/alembic/` | Migraciones (inicializar Alembic aquí) |
| `server/app/repositories/match_repository.py` | Consultas de partidas |
| `server/app/services/match_service.py` | Crear y unirse a partidas (Factory, RN-04) |
| `server/app/api/routes/matches.py` | Endpoints de partidas |
| `server/app/realtime/` | WebSocket: movimientos y posiciones |
| `client/src/` | Arena, lobby, captura de teclado y conexión WebSocket |
| `server/tests/test_matches.py` | Pruebas de partidas |

### Francisco — Rol C: Infraestructura, hardware y gestión

| Carpeta | Contenido |
| --- | --- |
| `hardware/` | Contrato de mensajes, simulador y firmware del ESP32 |
| `docs/` | ADRs, diagramas, estrategia de ramas |
| `.github/`, `docker-compose.yml`, `Dockerfile` | CI y contenedores |

### Cosas compartidas (coordinar antes de tocar)

- **Modelo `User`:** lo necesita Luis para auth, pero las tablas y migraciones son de Julián.
  Julián crea el modelo de usuarios **primero**, con los campos que Luis le pida
  (usuario, correo, hash, correo_verificado, etc.).
- **`server/app/main.py`:** cada uno solo agrega su línea `include_router`.
- **`requirements.txt`:** si agregan una librería, pónganla ahí con versión y avisen en el grupo.
- **Formato de mensajes del WebSocket:** Julián y Francisco usan el mismo formato para teclado y hardware.

---

## 6. Cómo trabajar cada tarea (GitHub Desktop)

`main` y `develop` están protegidas: **no se puede hacer push directo**. Todo entra por Pull Request.

1. **Actualizar develop:** *Current branch* → `develop` → *Fetch origin* → *Pull origin*.
2. **Crear su rama:** *Branch → New branch* → nombre `feature/US-01-registro`, basada en `develop`.
3. **Programar** y hacer commits pequeños. Mensaje con el ID del Board:
   `feat(auth): valida correo duplicado AB#45`
4. **Antes de subir**, correr en `server/`:

   ```bash
   ruff check .        # si hay errores de formato: ruff check . --fix
   pytest
   ```

5. **Publicar la rama:** *Publish branch*.
6. **Abrir el PR:** *Branch → Create pull request* → base `develop`. Explicar qué hace y qué US cubre.
7. **Esperar** el CI en verde y la aprobación de otro integrante.
8. **Merge** del PR en GitHub y borrar la rama.
9. Volver a `develop` y hacer *Pull*.

**Reglas del repo:**

- PR obligatorio hacia `main` y `develop`.
- 1 aprobación de otro integrante (no se puede aprobar el propio PR).
- Los checks "Lint y pruebas del backend" y "Build de la imagen Docker" deben pasar.
- Prohibido el force push.

**Revisar PRs de los demás también es parte del trabajo** y cuenta en el DoD. Revisen en menos de un día.

---

## 7. Azure Boards

- Al empezar una Task: moverla a **Doing**.
- Al terminarla (PR mergeado y cumple el DoD): moverla a **Done**.
- Actualizar horas restantes en cada reunión.
- Si algo los bloquea: crear un **Impediment**. Si encuentran un error: crear un **Bug**.
- Poner `AB#ID` en commits y PRs para que se vinculen solos.

---

## 8. Problemas comunes

| Problema | Solución |
| --- | --- |
| `docker compose` no funciona | Abrir Docker Desktop y esperar a que diga "running" |
| Error de puerto 5432 ocupado | Tienen PostgreSQL instalado en su compu: deténganlo o avisen para cambiar el puerto |
| `/health/db` dice "no disponible" | Revisar que exista el `.env` y reiniciar con `docker compose down` y `docker compose up` |
| El CI sale en rojo | Abrir el check en el PR, leer el error, corregir y hacer otro commit en la misma rama |
| GitHub no me deja hacer push a develop | Es correcto: hay que crear una rama y abrir un PR |
| Cambié `requirements.txt` y no lo toma | `docker compose up --build` para reconstruir la imagen |

Dudas: al grupo, antes de quedarse trabados.
