# ADR 0010: Despliegue en la nube con una máquina virtual y Caddy

- **Categoría:** infraestructura y operaciones (no es un patrón de diseño)
- **Estado:** Implementado (Sprint 3). En producción desde el 13/11/2026
- **Fecha:** 2026-11-13
- **Relacionado:** ADR 0001 (stack y Docker Compose), ADR 0002 (cliente móvil con pygbag)

## Contexto

El enunciado del Sprint 3 pide **despliegue en nube pública o privada con entrega continua**, y es
parte de la evidencia de DevOps que se califica. El tema no se vio en clase, así que la decisión se
tomó buscando lo más simple de sostener por un equipo de tres personas en tres semanas.

Lo que el despliegue tiene que resolver:

- El juego usa **WebSocket** para la partida en tiempo real (ADR 0001), no solo peticiones HTTP.
- El **cliente móvil** es una página web compilada con pygbag (ADR 0002). Los navegadores de los
  celulares exigen **HTTPS**; además, desde una página servida por `https://` no se puede llamar a
  un backend por `http://` sin que el navegador lo bloquee (contenido mixto).
- Ya existe un `docker-compose.yml` que levanta PostgreSQL y el backend. Repetir esa definición en
  otra tecnología sería duplicar configuración.
- El presupuesto es el crédito de estudiante (US$100 de Azure for Students, sin tarjeta).
- La entrega es el 23/11 y la defensa el 5/12: después de eso la infraestructura se borra.

## Decisión

Desplegar en una **máquina virtual Ubuntu en Azure** el mismo Docker Compose del proyecto, con un
servicio más: **Caddy** como proxy inverso.

| Pieza | Para qué | Archivo |
| --- | --- | --- |
| VM Ubuntu 24.04 (`vm-reactor`, Standard_B2ats_v2, northcentralus) | Corre Docker | — |
| `db` + `server` | Los mismos contenedores de desarrollo, sin publicar puertos | `docker-compose.prod.yml` |
| `web` (Caddy) | HTTPS automático, `/api/*` al backend y el cliente pygbag en `/` | `deploy/Caddyfile`, `deploy/web.Dockerfile` |
| Entrega continua | Al pasar el CI en `develop`: SSH → `git reset --hard` → `docker compose up -d --build` → verifica `/api/health/db` | `.github/workflows/deploy.yml` |
| Guía de operación | Crear la VM, secretos, logs, volver atrás, borrar todo | `docs/despliegue.md` |

```
Celular / navegador ──https──┐
PC (cliente pygame) ─https/wss┤
                              ▼
               VM Ubuntu (Azure) · puertos 22, 80, 443
               ┌──────────────────────────────────────────┐
               │ web (Caddy) :80 :443                     │
               │   /api/*  ──► server (FastAPI) :8000 ──► db (PostgreSQL 16)
               │   /       ──► cliente pygbag (archivos)  │
               └──────────────────────────────────────────┘
```

**Decisiones concretas y por qué:**

- **Un solo origen para todo.** Caddy sirve la página del cliente y, bajo `/api`, el backend. Así
  no hay contenido mixto ni CORS entre dominios, y el WebSocket viaja por `wss://` sobre la misma
  conexión. El cliente arma su URL en `url_backend_web()` (`client/src/config.py`): con `https`
  usa `https://<host>/api`; con `http` (servidor de pruebas de pygbag en la red local) sigue
  usando el puerto 8000 como antes.
- **Solo 22, 80 y 443 abiertos.** PostgreSQL (5432) y el backend (8000) no se publican: solo se
  llega a ellos desde dentro de la red de Docker. Reduce la superficie expuesta (RNF de
  seguridad).
- **Se despliega desde `develop`, no desde `main`.** A `main` solo se mergea una vez por sprint, y
  con eso no habría nada que mostrar como entrega continua. Desplegar en cada merge a `develop`
  hace que la nube siempre tenga lo último y que el despliegue se ejercite muchas veces antes de
  la demo.
- **El despliegue depende del CI.** El workflow se dispara con `workflow_run` y solo corre si el
  CI terminó en `success`: nunca se despliega una versión que no compila o no pasa las pruebas.
- **La versión desplegada es el commit exacto que pasó el CI** (`git reset --hard <sha>`), no "lo
  último de la rama", para que lo probado y lo desplegado sean lo mismo.
- **Los secretos no están en el repo.** El `.env` de producción vive solo en la VM; GitHub guarda
  `VM_HOST`, `VM_USER` y `VM_SSH_KEY` como secretos del repositorio.
- **Las migraciones corren solas** al arrancar el contenedor `server` (`alembic upgrade head`), así
  que no hay un paso manual de base de datos en cada despliegue.

## Alternativas consideradas

| Alternativa | Por qué no |
| --- | --- |
| Azure App Service o Container Apps | Son más "de la nube" y no hay que administrar un servidor, pero obligan a definir la infraestructura otra vez fuera del Compose, y la base de datos administrada se come el crédito rápido. Con una VM se usa tal cual lo que ya funciona en local |
| Kubernetes (AKS) | Desproporcionado para dos contenedores; más conceptos nuevos que los que el equipo puede aprender en tres semanas, y el clúster administrado cuesta más que el crédito disponible |
| Plataformas gratuitas (Render, Railway, Fly.io) | El nivel gratuito duerme la aplicación por inactividad, lo que rompe una partida en tiempo real, y varias piden tarjeta |
| Nginx en vez de Caddy | Nginx exige configurar certbot y renovar los certificados aparte. Caddy saca y renueva el certificado de Let's Encrypt solo, con tres líneas de configuración |
| Dominio propio | No hace falta: Azure da gratis `control-reactor.northcentralus.cloudapp.azure.com` con la etiqueta DNS de la IP pública, y Let's Encrypt emite certificados para ese nombre |
| Desplegar también desde `main` | Se mantiene para la entrega final; `develop` es el que se despliega continuamente |

## Consecuencias

**Positivas**

- El cliente del celular funciona por HTTPS sin configurar nada, que era el requisito que obligaba
  a tener proxy y certificado.
- Lo que corre en la nube es lo mismo que corre en la PC de cada uno: un solo `docker compose`, con
  diferencias acotadas al archivo de producción.
- Cada merge a `develop` deja una versión desplegada y verificada, y el historial de Actions sirve
  como evidencia de entrega continua para la calificación.
- Volver atrás es barato: `git reset --hard <commit>` y `./deploy/desplegar.sh` en la VM.

**Negativas**

- Hay un servidor que administrar (actualizaciones del sistema, disco, reinicios): es el costo de
  no usar una plataforma administrada.
- La VM tiene 1 GB de RAM; construir las imágenes la llena, por eso hubo que agregar 2 GB de swap.
- Un solo servidor es un único punto de falla y no escala horizontalmente. Para este proyecto no es
  problema: la cantidad de jugadores es la de una demo. El límite de una sola instancia del backend
  ya estaba anotado en el ADR 0003 (los motores de partida viven en memoria).
- La infraestructura depende de la cuenta de estudiante de un integrante y del crédito. Plan B
  documentado: correr la demo en local con `docker compose up`.
- El despliegue automático corre con una llave SSH guardada en GitHub; si se filtrara, daría acceso
  a la VM. Por eso es una llave aparte, usada solo por el workflow.

## Notas de operación

- La guía completa (crear la VM, secretos, logs, volver atrás) está en `docs/despliegue.md`.
- **Al terminar la defensa** hay que borrar todo para no gastar crédito:
  `az group delete -n rg-control-reactor`.
- Pendiente: configurar SMTP en el `.env` de producción. Sin eso, los correos de verificación solo
  se imprimen en los logs del contenedor y no se puede crear una cuenta nueva desde la nube.
