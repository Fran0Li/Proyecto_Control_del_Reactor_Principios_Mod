# Diagrama de componentes

Componentes del sistema y las interfaces por las que se comunican. Las cajas con borde punteado
están planificadas (todavía no están en `develop`).

```mermaid
flowchart LR
    subgraph HW["Control físico"]
        FW["Firmware Arduino<br/>control_reactor.ino"]
        SIM["Simulador del control<br/>hardware/simulator"]
    end

    subgraph CLI["Cliente del juego: pygame-ce en PC, pygbag en el navegador"]
        PANT["Pantallas<br/>registro, lobby y buscar partida"]
        JUEGO["Pantalla de juego<br/>US-25"]:::plan
        ENT["Fuentes de entrada<br/>FuenteEntrada, Adapter"]
        APIC["api_client"]
        HTTP["red/http<br/>requests o fetch"]
        WSC["red/websocket y realtime_client<br/>websockets o WebSocket"]
    end

    subgraph SRV["Backend FastAPI"]
        RAUTH["routes/auth"]
        RPART["routes/partidas"]
        RCANAL["routes/canal_partida<br/>WebSocket"]
        RHEALTH["routes/health"]
        CM["ConnectionManager<br/>publicar-suscribir por partida"]
        MOTOR["MotorPartida<br/>Observer, US-25"]:::plan
        SREG["RegistroService"]
        SPART["PartidaService"]
        FACT["PartidaFactory"]
        SEC["PasswordHasher<br/>scrypt"]
        REPO["Repositorios<br/>Usuario y Partida"]
        MOD["Modelos SQLAlchemy"]
        MIG["Migraciones Alembic"]
    end

    DB[("PostgreSQL 16")]
    GOOGLE["Google OAuth 2.0<br/>US-04"]:::plan
    SMTP["Servidor SMTP<br/>US-02 y US-05"]:::plan

    FW -- "USB Serial 115200<br/>HELLO, BTN, HB" --> ENT
    SIM -- "socket://localhost:7777<br/>mismas líneas" --> ENT
    ENT -- "control, estado" --> JUEGO
    PANT --> APIC
    APIC --> HTTP
    JUEGO --> WSC
    PANT --> WSC

    HTTP -- "REST JSON" --> RAUTH
    HTTP -- "REST JSON" --> RPART
    HTTP -- "REST JSON" --> RHEALTH
    WSC -- "WebSocket<br/>/ws/partidas/id" --> RCANAL

    RAUTH --> SREG
    RPART --> SPART
    SREG --> SEC
    SREG --> REPO
    SPART --> FACT
    SPART --> REPO
    RCANAL --> SPART
    RCANAL --> CM
    MOTOR -.-> CM
    REPO --> MOD
    MOD -- "SQL" --> DB
    MIG -- "esquema" --> DB
    RHEALTH -- "SELECT 1" --> DB

    RAUTH -.-> GOOGLE
    SREG -.-> SMTP

    classDef plan stroke-dasharray: 5 5
```

## Componentes

| Componente | Responsabilidad | Código | Estado |
| --- | --- | --- | --- |
| Firmware Arduino | Lee los 5 botones (D2–D6) con antirrebote y envía cambios por Serial | `hardware/firmware/control_reactor/` | Implementado |
| Simulador del control | Ventana con los 5 botones que envía las mismas líneas por un socket local | `hardware/simulator/` | Implementado |
| Fuentes de entrada | Convierten teclado, táctil, Serial y simulador en `(control, estado)` (Adapter) | `client/src/entrada/` | Serial y simulador implementados; teclado y táctil en `prototipos/cliente-movil/` |
| Pantallas | Registro, lobby y buscar o unirse a partidas; llaman a la API desde tareas async sin congelar la ventana | `client/src/screens/` | Implementado |
| Pantalla de juego | Dibuja la arena y envía las entradas por WebSocket | — | Planificado (US-25) |
| `api_client` | Funciones async por endpoint; traduce errores de la API a mensajes | `client/src/api_client.py` | Implementado |
| `red/http` | HTTP en escritorio (`requests` en un hilo) y en el navegador (`fetch`) | `client/src/red/http.py` | Implementado |
| `red/websocket` y `realtime_client` | WebSocket en escritorio y en el navegador, y canal de la partida que usan las pantallas | `client/src/red/websocket.py`, `client/src/realtime_client.py` | Implementado (US-08) |
| Rutas REST | Validan las peticiones y traducen errores a códigos HTTP | `server/app/api/routes/` | `auth` (registro), `partidas` (crear, listar y unirse) y `health` |
| Canal de la partida | WebSocket por partida: verifica que el jugador participe y lo suscribe al canal | `server/app/api/routes/canal_partida.py` | Implementado (US-08) |
| `ConnectionManager` | Guarda los jugadores conectados a cada partida y les difunde los mensajes (publicar-suscribir) | `server/app/realtime/connection_manager.py` | Implementado (US-08) |
| `MotorPartida` | Aplica entradas, mueve jugadores y notifica a los observadores | — | Planificado (US-25; ver ADR 0003) |
| Servicios | Reglas de negocio | `server/app/services/` | `RegistroService`, `PartidaService`, `PartidaFactory` |
| `PasswordHasher` | Hash y verificación de contraseñas con scrypt | `server/app/core/security.py` | Implementado |
| Repositorios | Acceso a datos (Repository) | `server/app/repositories/` | Implementado |
| Modelos y migraciones | Tablas en SQLAlchemy y versiones del esquema en Alembic | `server/app/models/`, `server/alembic/` | Implementado |
| PostgreSQL | Usuarios, partidas, participaciones, eventos y ranking | Contenedor `db` | Implementado |
| Google OAuth | Inicio de sesión con Google | — | Planificado (US-04) |
| Servidor SMTP | Correos de verificación y recuperación de contraseña | — | Planificado (US-02, US-05) |

## Interfaces

| Interfaz | Entre | Formato | Definida en |
| --- | --- | --- | --- |
| Serial | Arduino → cliente | Líneas ASCII a 115200 baudios: `HELLO`, `BTN <botón> PRESS/RELEASE`, `HB` | `docs/contrato-api-hardware.md`, capa 1 |
| Socket local | Simulador → cliente | Las mismas líneas por `socket://localhost:7777` | `hardware/simulator/README.md` |
| REST | Cliente → backend | JSON: `POST /auth/registro`, `POST /partidas`, `GET /partidas`, `POST /partidas/{id}/unirse`, `GET /health`, `GET /health/db` | Documentación interactiva en `/docs` |
| WebSocket | Cliente ↔ backend | JSON con campo `tipo`: `entrada`, `dispositivo`, `error`, estado de la partida | `docs/contrato-api-hardware.md`, capa 2 |
| SQL | Backend → PostgreSQL | SQLAlchemy con `psycopg` | `server/app/db/session.py` |

Para el servidor no hay diferencia entre teclado, táctil, control físico o simulador: todos llegan
como el mismo mensaje `entrada`, con `origen` solo informativo.
