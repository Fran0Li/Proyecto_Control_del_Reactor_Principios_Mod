# Vista de despliegue

Dónde corre cada componente y cómo se conectan los nodos.

## Sprint 2: red local (desarrollo y demostración)

Todo corre en la red WiFi del equipo. El backend y la base de datos van en contenedores con
Docker Compose; el cliente corre en la PC de cada jugador o en el navegador del celular.

```mermaid
flowchart LR
    subgraph ARD["«dispositivo» Arduino Uno"]
        FW["firmware<br/>control_reactor.ino<br/>5 botones D2 a D6"]
    end

    subgraph PC["«dispositivo» PC del jugador · Windows"]
        CLI["cliente pygame-ce<br/>Python 3.12 · python main.py"]
        SIM["simulador del control<br/>opcional"]
    end

    subgraph CEL["«dispositivo» Celular · Chrome Android"]
        WEB["cliente WebAssembly<br/>generado con pygbag"]
    end

    subgraph HOST["«servidor» PC anfitriona del equipo"]
        PYGBAG["servidor web de pygbag<br/>puerto 8001"]
        subgraph COMPOSE["«entorno» Docker Compose"]
            SRV["contenedor server<br/>python:3.12-slim · uvicorn<br/>FastAPI · puerto 8000"]
            DB[("contenedor db<br/>postgres:16 · puerto 5432")]
            VOL[/"volumen pgdata"/]
        end
    end

    FW -- "USB Serial · 115200 baudios" --> CLI
    SIM -- "socket://localhost:7777" --> CLI
    CLI -- "HTTP REST y WebSocket · :8000" --> SRV
    WEB -- "HTTP · :8001<br/>descarga la página" --> PYGBAG
    WEB -- "fetch y WebSocket · :8000<br/>con CORS" --> SRV
    SRV -- "TCP 5432 · SQL" --> DB
    DB --- VOL
```

| Nodo | Software | Cómo se levanta |
| --- | --- | --- |
| Arduino Uno | `hardware/firmware/control_reactor/control_reactor.ino` | Se carga con Arduino IDE; se conecta por USB a la PC del jugador |
| PC del jugador | Python 3.12, `pygame-ce`, `requests`, `pyserial` | `cd client && python main.py` |
| Celular | Navegador con el cliente compilado por pygbag | Abrir `http://<IP de la PC anfitriona>:8001` en la misma red |
| PC anfitriona | Docker Desktop y pygbag | `docker compose up --build` y `pygbag --bind <IP real> --port 8001 .` dentro de `client/` |
| Contenedor `server` | Imagen de `server/Dockerfile` | Lo levanta Compose cuando `db` pasa el healthcheck |
| Contenedor `db` | `postgres:16` con volumen `pgdata` | Lo levanta Compose; los datos sobreviven a reinicios |

Notas:

- El Arduino siempre se conecta a la PC del jugador, no al servidor (contrato de hardware). En el
  celular no hay control físico: se juega con botones táctiles.
- La PC anfitriona puede ser la misma PC de un jugador.
- `pygbag --bind` necesita la IP real de la PC, no `0.0.0.0` (ADR 0002).
- Las variables de entorno van en `.env` (plantilla en `.env.example`); el `.env` no se sube al
  repositorio.

## Sprint 3: despliegue en la nube (propuesto)

El enunciado pide despliegue en la nube. El proveedor está por definir; esta es la forma que debe
tener sin importar cuál se elija.

```mermaid
flowchart LR
    subgraph JUG["Jugadores"]
        PCJ["PC con cliente pygame<br/>y Arduino por USB"]
        CELJ["Celular con navegador"]
    end

    subgraph NUBE["«nube» proveedor por definir"]
        PROXY["proxy HTTPS<br/>certificado TLS"]
        STATIC["página del cliente web<br/>build de pygbag"]
        SRVN["contenedor server<br/>FastAPI"]
        DBN[("PostgreSQL<br/>contenedor o servicio administrado")]
    end

    GOOG["Google OAuth 2.0"]
    MAIL["Servidor SMTP"]

    PCJ -- "HTTPS y wss" --> PROXY
    CELJ -- "HTTPS y wss" --> PROXY
    PROXY --> STATIC
    PROXY --> SRVN
    SRVN --> DBN
    SRVN -- "OAuth" --> GOOG
    SRVN -- "SMTP con TLS" --> MAIL
```

- Si la página se sirve por HTTPS, el navegador exige `wss://` para el WebSocket, así que el
  backend necesita certificado TLS (ADR 0002).
- `CORS_ORIGENES` deja de ser `*` y pasa a ser el dominio del cliente web.
- La imagen del backend es la misma que construye el CI.

## Pipeline de CI

Cada Pull Request y cada push a `develop` o `main` corre `.github/workflows/ci.yml` en GitHub
Actions. Los cuatro jobs se configuran como checks requeridos en la ruleset de `develop`.

```mermaid
flowchart TB
    PR["Pull Request o push<br/>a develop o main"] --> BACK
    PR --> CLIJ
    PR --> FWJ

    subgraph BACK["Lint y pruebas del backend"]
        direction LR
        B1["ruff"] --> B2["alembic upgrade head<br/>sobre postgres:16 temporal"] --> B3["pytest<br/>unitarias e integración"]
    end
    BACK --> DOCK["Build de la imagen Docker"]

    subgraph CLIJ["Lint y pruebas del cliente"]
        direction LR
        C1["ruff"] --> C2["pytest<br/>sin pantalla, SDL dummy"]
    end

    subgraph FWJ["Firmware del control"]
        direction LR
        F1["compilar para Arduino Uno"] --> F2["pruebas en la PC<br/>5 botones y joystick"]
    end
```
