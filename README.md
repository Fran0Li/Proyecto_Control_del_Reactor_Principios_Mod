# Control del Reactor

Videojuego multijugador competitivo con integración de hardware.
Proyecto CE-1105 Principios de Modelado en Ingeniería, TEC, II Semestre 2026.

## Estructura

| Carpeta | Contenido |
| --- | --- |
| `server/` | Backend en FastAPI: API REST, WebSocket del juego y acceso a PostgreSQL |
| `client/` | Cliente del juego en pygame |
| `hardware/` | Firmware del control físico y simulador de botones |
| `docs/` | ADRs, estrategia de ramas y documentación técnica |
| `.github/workflows/` | Pipeline de CI (GitHub Actions) |

Dentro de `server/app/` el código va por capas:

- `api/routes/`: endpoints REST (solo reciben la petición y llaman a un servicio).
- `realtime/`: WebSocket de las partidas.
- `services/`: lógica de negocio.
- `repositories/`: acceso a datos (patrón Repository).
- `models/`: modelos de SQLAlchemy.
- `core/`: configuración.
- `db/`: conexión a la base de datos.

## Cómo levantar el backend

Requisitos: Docker Desktop.

```bash
cp .env.example .env        # en Windows: copy .env.example .env
docker compose up --build
```

- API: http://localhost:8000
- Documentación interactiva: http://localhost:8000/docs
- Estado del servidor: http://localhost:8000/health
- Estado de la base de datos: http://localhost:8000/health/db

## Desarrollo local sin Docker

```bash
cd server
python -m venv .venv
.venv\Scripts\activate          # Windows  
pip install -r requirements-dev.txt
pytest
ruff check .
```

## Cliente pygame

```bash
cd client
pip install -r requirements.txt
python main.py
```

Con el backend corriendo, la ventana muestra si el servidor responde.

## Forma de trabajo

Ver [docs/estrategia-de-ramas.md](docs/estrategia-de-ramas.md). Resumen:

- Nunca se trabaja directo en `main` ni en `develop`.
- Una rama por historia: `feature/US-XX-descripcion`.
- Todo entra a `develop` por Pull Request, con una aprobación y el CI en verde.
- Los commits mencionan el work item de Azure Boards: `AB#45`.
