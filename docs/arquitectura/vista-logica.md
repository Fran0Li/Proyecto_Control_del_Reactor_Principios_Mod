# Vista lógica

Cómo está organizado el sistema por responsabilidades, independientemente de dónde corre cada
parte. Los patrones están justificados en el ADR 0003 (arquitectura) y en los ADRs 0004 a 0009 (diseño).

## Capas del sistema

```mermaid
flowchart TB
    PRES["<b>Presentación</b> · cliente pygame<br/>pantallas de registro, lobby y juego<br/>fuentes de entrada: teclado, táctil, Arduino, simulador"]
    COM["<b>Comunicación</b><br/>REST: api_client y red/http · tiempo real: red/ws"]
    API["<b>API del backend</b><br/>rutas REST auth, partidas, health · canal WebSocket realtime"]
    NEG["<b>Lógica de negocio</b><br/>RegistroService, PartidaService, PartidaFactory<br/>MotorPartida, sujeto del Observer"]
    PER["<b>Persistencia</b><br/>repositorios y modelos SQLAlchemy"]
    DB[("PostgreSQL")]

    PRES --> COM --> API --> NEG --> PER --> DB
```

| Capa | Qué hace | Qué no hace |
| --- | --- | --- |
| Presentación | Dibuja, lee entradas y muestra lo que manda el servidor | No decide movimientos, puntajes ni ganador |
| Comunicación | Habla con el backend igual en escritorio y en navegador (ADR 0002) | No conoce las pantallas |
| API | Valida peticiones con Pydantic y traduce errores a códigos HTTP o mensajes `error` | No tiene reglas de negocio ni SQL |
| Lógica de negocio | Aplica las reglas (RN-01, RN-04…), crea partidas y mueve el juego | No conoce HTTP ni WebSocket |
| Persistencia | Lee y escribe en PostgreSQL | No decide nada del juego |

Cada capa solo depende de la de abajo, y en el backend las dependencias se inyectan (la sesión
con `Depends(get_session)`, el repositorio y la fábrica por el constructor del servicio).

## Modelo de datos

Tablas actuales (`server/app/models/`, migración inicial en `server/alembic/versions/`).

```mermaid
classDiagram
    class Usuario {
        id
        nombre_usuario: único
        correo: único
        correo_verificado
        contrasena_hash
        fecha_registro
    }
    class Partida {
        id
        estado: esperando, en_curso, finalizada
        escenario
        tiempo_limite_segundos
        puntuacion_objetivo
        fecha_inicio
        fecha_fin
    }
    class Participacion {
        id
        jugador_id
        partida_id
        puntaje_final
        posicion_final
    }
    class Evento {
        id
        partida_id
        tipo
        timestamp
    }
    class RankingGlobal {
        jugador_id
        puntos_totales
        victorias
        actualizado_en
    }
    Usuario "1" -- "0..*" Participacion : juega
    Partida "1" -- "1..*" Participacion : tiene
    Partida "1" -- "0..*" Evento : registra
    Usuario "1" -- "0..1" RankingGlobal : acumula
```

Reglas que el modelo ayuda a cumplir:

- **RN-01:** `correo` y `nombre_usuario` son únicos en la base de datos, además de la validación
  del servicio.
- **RN-04:** un jugador no puede estar en dos partidas activas (`esperando` o `en_curso`); lo
  revisa `PartidaRepository.jugador_en_partida_activa`.
- El historial de partidas sale de `Participacion` y el top 10 de `RankingGlobal`.

## Flujo de una entrada del control físico

Cómo viaja un botón presionado hasta la pantalla de todos los jugadores. La parte del servidor
se implementa con US-08 y US-25.

```mermaid
sequenceDiagram
    participant A as Arduino
    participant F as EntradaSerial
    participant C as Cliente pygame
    participant W as Canal WebSocket
    participant M as MotorPartida
    participant O as Observadores

    A->>F: BTN UP PRESS
    F->>C: (arriba, presionado)
    C->>W: entrada, control arriba, origen hardware, seq
    W->>M: aplicar_entrada(jugador, arriba, presionado)
    Note over M: en cada tick mueve al jugador<br/>y valida colisiones
    M->>O: estado_actualizado
    O-->>C: estado de la partida a todos los clientes
    C->>C: dibuja la nueva posición
```

Si el Arduino deja de enviar latidos (`HB`) durante 3 s, `EntradaSerial` suelta los controles
presionados y el cliente envía `dispositivo: desconectado`, como define el contrato de hardware.
