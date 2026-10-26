# ADR 0003: Patrones de arquitectura y de diseño

- **Estado:** Aceptado
- **Fecha:** 2026-10-11 (actualizado el 2026-10-18 con los drivers y el canal en tiempo real, y el
  2026-10-20 con el motor de partida y las entradas del jugador; el 2026-10-25 los patrones de
  diseño pasaron a los ADRs 0004 a 0009)
- **Relacionado:** ADR 0001 (stack), ADR 0002 (cliente móvil), ADRs 0004 a 0009 (patrones de
  diseño), `docs/contrato-api-hardware.md`, `docs/arquitectura/`

## Contexto

El Sprint 2 pide seleccionar y justificar los patrones de arquitectura y de diseño del producto,
con al menos un patrón creacional, uno estructural y uno de comportamiento. Parte de ellos ya está
en el código de `develop`. Este ADR documenta los **patrones de arquitectura**; cada **patrón de
diseño** tiene su propio ADR (0004 a 0009), con los roles del patrón y nuestras clases. Los nombres
siguen los del curso (Tema 4 para arquitectura: cliente-servidor, capas, publicar-suscribir,
monolito frente a microservicios).

## Drivers arquitectónicos

Los requisitos que más pesan en la arquitectura y la decisión que responde a cada uno:

| Driver | Origen | Decisión |
| --- | --- | --- |
| Movimientos reflejados en menos de 500 ms | RNF-02 | Canal WebSocket por partida y servidor autoritativo; medido: 33 ms en el celular (ADR 0002) |
| Al menos dos jugadores simultáneos | RNF-01 | Publicar-suscribir: cada mensaje del servidor llega a todos los jugadores de la partida |
| Computadora y celular | RNF-07 | Un solo cliente pygame, compilado con pygbag para el navegador (ADR 0002) |
| Control físico de 5 botones | RNF-10 | Arduino por USB Serial a la PC del jugador; Adapter para que el resto del cliente no note la diferencia |
| Agregar funcionalidades sin rehacer lo existente | RNF-06 | Capas, Repository, Factory y Observer: lo nuevo se agrega como clase nueva |
| Contenedores, base de datos y nube | RNF-05, RNF-09, RNF-11 | Backend y PostgreSQL en Docker Compose; la misma imagen sirve para la nube |
| Equipo de tres personas, sprints de un mes | Restricción del proyecto | Un solo backend (monolito modular) en vez de microservicios |

## Resumen

| Patrón | Tipo | Dónde | Estado |
| --- | --- | --- | --- |
| Cliente-servidor de 3 niveles, cliente delgado | Arquitectura | Cliente pygame ↔ backend FastAPI ↔ PostgreSQL | REST, canal WebSocket y movimiento en el servidor implementados; arena del cliente con US-25 |
| Arquitectura en capas (monolito modular) | Arquitectura | `server/app/`: `api` → `services` → `repositories` → `models` | Implementado |
| Publicar-suscribir | Arquitectura | Canal WebSocket de cada partida (`ConnectionManager`) | Implementado (US-08) |
| Repository | Persistencia (no GoF) | `UsuarioRepository`, `PartidaRepository`, `TokenRepository` | Implementado ([ADR 0009](0009-repository-persistencia.md)) |
| **Factory** | **Creacional** | `PartidaFactory` | Implementado, US-07 ([ADR 0004](0004-factory-creacion-de-partidas.md)) |
| **Adapter** | **Estructural** | `FuenteEntrada` con `Teclado`, `Tactil` y `EntradaSerial` | Implementado, AB#40 ([ADR 0005](0005-adapter-fuentes-de-entrada.md)) |
| **Observer** | **Comportamiento** | `MotorPartida` → `NotificadorWebSocket` | Implementado, US-25 ([ADR 0006](0006-observer-motor-de-partida.md)) |
| Facade | Estructural | `api_client` del cliente | Implementado ([ADR 0007](0007-facade-api-client.md)) |
| Bridge | Estructural | `CanalPartida` ↔ `Conexion` (escritorio y navegador) | Implementado ([ADR 0008](0008-bridge-conexion-del-cliente.md)) |
| Strategy | Comportamiento | Movimiento de los guardianes | Planificado para el Sprint 3 (ADR 0006) |
| State | Comportamiento | Estados del jugador (activo, escudado, aturdido, eliminado) | Planificado para el Sprint 3 (ADR 0006) |

## Patrones de arquitectura

### Cliente-servidor de 3 niveles con cliente delgado

| Nivel | Qué corre | Dónde |
| --- | --- | --- |
| Presentación | Cliente pygame: pantallas, entradas y dibujo de la arena | PC del jugador o navegador del celular |
| Lógica | Backend FastAPI: reglas, partidas y canal en tiempo real | Contenedor `server` |
| Datos | PostgreSQL | Contenedor `db` |

El cliente es **delgado**: solo dibuja y envía entradas. El servidor es **autoritativo**: decide el
movimiento, las colisiones, los puntajes y el ganador.

- **Por qué:** con varios jugadores y varias fuentes de entrada (teclado, táctil, Arduino), una
  sola fuente de verdad evita trampas y estados distintos entre clientes.
- **Consecuencia:** el cliente necesita una conexión en tiempo real (WebSocket) para recibir el
  estado de la partida. La latencia medida en el prototipo móvil fue de 33 ms, lejos del límite de
  500 ms (ADR 0002).

### Arquitectura en capas (backend)

| Capa | Carpeta | Responsabilidad | Ejemplo |
| --- | --- | --- | --- |
| API | `api/routes/` | Validar la petición (Pydantic) y traducir errores a códigos HTTP | `auth.py`, `partidas.py` |
| Tiempo real | `realtime/`, `api/routes/canal_partida.py` | Canal WebSocket de cada partida | `ConnectionManager` (US-08) |
| Servicios | `services/` | Reglas de negocio (RN-01, RN-04…) | `RegistroService`, `PartidaService` |
| Repositorios | `repositories/` | Consultas y escrituras en la base de datos | `PartidaRepository` |
| Modelos | `models/` | Tablas de SQLAlchemy | `Usuario`, `Partida`, `Evento` |

Cada capa solo llama a la de abajo. Un endpoint nunca hace consultas SQL y un servicio nunca
devuelve códigos HTTP.

- **Por qué:** cada integrante trabaja en una capa o historia sin pisar a los demás, y los
  servicios se prueban sin levantar el servidor.
- **Consecuencia:** hay más archivos por historia (ruta, servicio, repositorio), pero cada uno es
  corto y tiene una sola razón para cambiar.
- **Monolito modular en vez de microservicios:** el ERS del Sprint 1 proponía microservicios
  (autenticación, servidor de juego, ranking y gateway de hardware) detrás de un balanceador. Para
  un equipo de tres personas eso multiplica despliegues, configuraciones y pruebas de integración
  sin una necesidad real de escalar por separado. Se elige un solo backend en capas; si más adelante
  hace falta, los módulos `auth`, `partidas` y `realtime` ya están separados.

### Publicar-suscribir en el canal de cada partida

Cada partida tiene un canal (`/ws/partidas/{id}`). Los jugadores se **suscriben** al conectarse y
el servidor **publica** en el canal con `ConnectionManager.difundir()`: todos los suscriptores
reciben el mensaje (`jugador_conectado`, `jugador_desconectado` y, con US-25, el estado de la
partida).

- **Por qué:** cumple RNF-01 y RNF-02 con una sola conexión abierta por jugador, sin que el cliente
  tenga que preguntar cada cierto tiempo.
- **Desacoplamiento:** quien publica no conoce a los suscriptores; una conexión caída se descarta
  sin afectar a los demás.
- **Límite conocido:** los canales viven en la memoria de un solo proceso del backend. Con varias
  instancias detrás de un balanceador haría falta un intermediario (patrón Broker, por ejemplo Redis
  publicar-suscribir). Para el alcance del curso basta una instancia.
- **Identificación del jugador:** el canal saca al jugador del token de la sesión (`?token=<JWT>`,
  AB#91) y verifica que participe en la partida; nadie puede hacerse pasar por otro.
- **Código:** `server/app/realtime/connection_manager.py`, `server/app/api/routes/canal_partida.py`;
  en el cliente, `client/src/realtime_client.py` sobre la interfaz `Conexion` de `client/src/red/`,
  con una implementación para escritorio y otra para el navegador (ADR 0002).

### Patrones de arquitectura vistos en el curso que no se usan

| Patrón | Por qué no |
| --- | --- |
| Microservicios | Ver arriba: más costo de operación que beneficio para tres personas |
| Orientado a eventos con bus de eventos (EDA) | El juego necesita respuestas inmediatas dentro de una partida; basta publicar-suscribir en memoria, sin un bus aparte |
| Broker | Solo hay un servidor; se volvería necesario con varias instancias (ver el límite de arriba) |
| Modelo-Vista-Controlador | El cliente es delgado y no tiene un modelo propio que sincronizar; el estado vive en el servidor |
| Maestro-esclavo | No hay trabajo que repartir entre nodos de cómputo |
| Tubería y filtros | No hay un flujo de datos por etapas; la única cadena (Serial → línea → entrada) es pequeña y queda dentro del Adapter |
| Peer-to-peer | Sin servidor autoritativo cada jugador podría alterar su propio estado |
| SOA | No hay otros sistemas de la organización con los que integrarse |

## Patrones de diseño

Cada patrón de diseño está en su propio ADR con el mismo formato: contexto, decisión (roles del
patrón con nuestras clases), alternativas consideradas, consecuencias y estado.

| ADR | Patrón | Categoría | Problema que resuelve | Estado |
| --- | --- | --- | --- | --- |
| [0004](0004-factory-creacion-de-partidas.md) | Factory | Creacional | Crear partidas válidas desde un solo lugar | Implementado |
| [0005](0005-adapter-fuentes-de-entrada.md) | Adapter | Estructural | Teclado, táctil, Arduino y simulador entregan el mismo mensaje `entrada` | Implementado |
| [0006](0006-observer-motor-de-partida.md) | Observer | Comportamiento | El motor avisa a los interesados sin conocerlos (WebSocket hoy; eventos y ranking en el Sprint 3) | Implementado; Strategy y State planificados |
| [0007](0007-facade-api-client.md) | Facade | Estructural | Las pantallas llaman al backend sin conocer la red | Implementado |
| [0008](0008-bridge-conexion-del-cliente.md) | Bridge | Estructural | El canal de la partida no depende de si corre en escritorio o en el navegador | Implementado |
| [0009](0009-repository-persistencia.md) | Repository | Persistencia (no cuenta para el mínimo) | Separar las reglas de negocio del SQL | Implementado |

El mínimo del proyecto (un creacional, un estructural y uno de comportamiento) lo cubren Factory,
Adapter y Observer, los tres ya en `develop` y con pruebas.

## Principios SOLID en el código actual

| Principio | Dónde se ve |
| --- | --- |
| Responsabilidad única | Rutas, servicios y repositorios separados; `protocolo_serial.py` solo interpreta líneas y `serial_entrada.py` solo lee el puerto |
| Abierto/cerrado | Nuevas fuentes de entrada (Adapter) y nuevos observadores sin modificar el código existente |
| Sustitución de Liskov | Cualquier `FuenteEntrada` sirve donde el cliente espera una fuente |
| Segregación de interfaces | `FuenteEntrada` trae métodos opcionales con implementación vacía; cada fuente redefine solo los que usa |
| Inversión de dependencias | `PartidaService` recibe el repositorio y la fábrica; el hash de contraseñas depende de la interfaz `PasswordHasher`; FastAPI inyecta la sesión con `Depends(get_session)` |

## Consecuencias

- Los patrones de arquitectura (cliente-servidor de 3 niveles, capas y publicar-suscribir) responden a
  los drivers de la tabla del inicio.
- Hay un patrón de cada tipo exigido: Factory (creacional), Adapter (estructural) y Observer (de
  comportamiento), más Facade, Bridge y Repository. Todos están en `develop` (ADRs 0004 a 0009).
- Los observadores del Sprint 3 (eventos y ranking) se agregan sin modificar el motor de partida.
- Los diagramas de componentes, la vista lógica y la de despliegue están en `docs/arquitectura/`
  y reemplazan las vistas del ERS del Sprint 1.
