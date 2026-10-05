# ADR 0001: Stack tecnológico

- **Estado:** Aceptado
- **Fecha:** 2026-10-04

## Contexto

El ERS del Sprint 1 proponía React y Node.js. El equipo tiene más experiencia en Python y
quiere desarrollar el juego con pygame. Se necesita un backend con REST y WebSocket,
persistencia en PostgreSQL, Docker y CI automático.

## Decisión

| Área | Tecnología |
| --- | --- |
| Lenguaje | Python |
| Cliente del juego | pygame |
| Backend REST + WebSocket | FastAPI |
| Base de datos | PostgreSQL con SQLAlchemy y Alembic |
| Pruebas | pytest |
| Contenedores | Docker y Docker Compose |
| Repositorio | GitHub |
| CI | GitHub Actions |
| Login social | Google (OAuth 2.0) |

Pendientes: servicio de correo, protocolo del control físico y cliente móvil.

## Justificación

- Un solo lenguaje en todo el proyecto reduce la curva de aprendizaje del equipo.
- FastAPI soporta WebSocket de forma nativa y genera documentación interactiva en `/docs`,
  lo que permite probar el backend sin el cliente.
- SQLAlchemy permite aplicar el patrón Repository y Alembic versiona el esquema.
- GitHub Actions vive junto al código y muestra el resultado en cada Pull Request.

## Consecuencias

- El backend y PostgreSQL corren en Docker; el cliente pygame corre en la máquina de cada jugador.
- El login con Google abre el navegador del sistema y el backend recibe el callback.
- pygame no corre nativo en móvil: hay que validar pygbag o definir otro cliente antes del Sprint 3.
- Las vistas de arquitectura del ERS deben actualizarse a este stack.
