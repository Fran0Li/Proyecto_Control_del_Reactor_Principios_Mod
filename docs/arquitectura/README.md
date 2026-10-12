# Arquitectura de Control del Reactor

Vistas de arquitectura del Sprint 2. Reemplazan las del ERS del Sprint 1, que se hicieron antes de
elegir el stack actual (ADR 0001) y el cliente móvil con pygbag (ADR 0002).

| Documento | Contenido | Work item |
| --- | --- | --- |
| [Vista lógica](vista-logica.md) | Capas del sistema, modelo de datos y flujo de una entrada del control | AB#80 |
| [Diagrama de componentes](componentes.md) | Componentes del cliente, el backend y el hardware, con sus interfaces | AB#79 |
| [Vista de despliegue](despliegue.md) | Nodos en red local (Sprint 2), despliegue en la nube (propuesto) y pipeline de CI | AB#80 |
| [ADR 0003: patrones](../adr/0003-patrones-de-arquitectura-y-diseno.md) | Patrones de arquitectura y de diseño, con su justificación | AB#81 |

## Resumen

- **Cliente-servidor con servidor autoritativo:** el cliente pygame (PC) o pygbag (celular) dibuja
  y envía entradas; el backend FastAPI decide el juego.
- **Backend en capas:** rutas → servicios → repositorios → modelos → PostgreSQL.
- **Hardware:** Arduino Uno por USB Serial a la PC del jugador, traducido en el cliente al mismo
  mensaje que el teclado (`docs/contrato-api-hardware.md`).
- **Contenedores:** backend y PostgreSQL con Docker Compose; la misma imagen se construye en el CI.
- **Patrones de diseño:** Factory (creacional), Adapter (estructural) y Observer (de
  comportamiento), además de Repository.

## Cambios respecto al ERS del Sprint 1

| ERS Sprint 1 | Ahora | Por qué |
| --- | --- | --- |
| Microservicios separados (autenticación, servidor de juego, ranking, gateway de hardware) detrás de un balanceador | Un solo backend FastAPI organizado en capas | Equipo de tres personas: un solo servicio es más simple de desplegar y probar (ADR 0003) |
| Clientes distintos: navegador, aplicación de escritorio y aplicación móvil | Un solo cliente pygame, compilado con pygbag para el navegador del celular | ADR 0002 |
| Frontend en React y backend en Node.js | pygame y FastAPI, todo en Python | ADR 0001 |
| Microcontrolador por MQTT o WiFi con un gateway en la nube | Arduino Uno por USB Serial a la PC del jugador, sin broker | Contrato de hardware |

## Cómo ver los diagramas

Los diagramas están en Mermaid: GitHub los dibuja directamente al abrir cada archivo. Para la Wiki
de Azure DevOps se copian los bloques cambiando ` ```mermaid ` por `::: mermaid` y cerrando con
`:::`.
