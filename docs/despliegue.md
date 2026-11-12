# Despliegue en la nube y entrega continua

El juego corre en una máquina virtual Ubuntu de Azure (suscripción **Azure for Students**) con el
mismo Docker Compose de desarrollo más **Caddy** como proxy inverso. Cada merge a `develop` que pasa
el CI se despliega solo (`.github/workflows/deploy.yml`).

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

| Archivo | Para qué |
| --- | --- |
| `docker-compose.prod.yml` | `db`, `server` y `web`. Solo `web` publica puertos (80 y 443) |
| `deploy/Caddyfile` | HTTPS automático (Let's Encrypt), `/api/*` al backend, cliente web en `/` |
| `deploy/web.Dockerfile` | Compila el cliente con pygbag y lo copia a la imagen de Caddy |
| `deploy/.env.prod.example` | Plantilla del `.env` de producción (el real vive solo en la VM) |
| `deploy/desplegar.sh` | `docker compose up -d --build` en la VM |
| `.github/workflows/deploy.yml` | Entrega continua: CI en verde en `develop` → SSH → desplegar → revisar `/api/health/db` |

Las migraciones corren solas al arrancar el contenedor `server` (`alembic upgrade head`).

## 1. Crear la VM (una sola vez, en portal.azure.com)

1. Activar **Azure for Students** con la cuenta @estudiantec.cr (100 USD, sin tarjeta).
2. **Máquinas virtuales → Crear**:
   - Grupo de recursos: `rg-control-reactor`. Nombre: `vm-reactor`.
   - Imagen: **Ubuntu Server 24.04 LTS (x64)**. Tamaño: **B1s** (o B2ats v2 si no hay B1s en la región).
   - Autenticación: **clave pública SSH**, usuario `reactor`, generar un par nuevo y descargar el `.pem`.
   - Puertos de entrada: **SSH (22), HTTP (80) y HTTPS (443)**. 8000 y 5432 quedan cerrados.
3. En la **IP pública** de la VM → Configuración → **Etiqueta de nombre DNS**: `control-reactor`.
   El dominio queda como `control-reactor.<region>.cloudapp.azure.com`.

## 2. Preparar la VM (una sola vez, por SSH)

```bash
ssh -i vm-reactor_key.pem reactor@control-reactor.<region>.cloudapp.azure.com

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && exit   # volver a entrar para que tome el grupo

# 2 GB de swap: la B1s tiene 1 GB de RAM y construir las imágenes la llena
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile
sudo swapon /swapfile && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Código y configuración
git clone -b develop https://github.com/Fran0Li/Proyecto_Control_del_Reactor_Principios_Mod ~/reactor
cd ~/reactor
cp deploy/.env.prod.example .env
openssl rand -hex 32   # una vez para JWT_SECRET y otra para POSTGRES_PASSWORD
nano .env              # DOMINIO, claves, CORS_ORIGENES y URL_PUBLICA con el dominio real

./deploy/desplegar.sh
```

Revisar `https://<dominio>/api/health/db` (debe decir `conectada`) y `https://<dominio>` (cliente web).

## 3. Conectar la entrega continua (una sola vez)

En la VM, una llave SSH solo para GitHub Actions:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/deploy_github -N "" -C "github-actions"
cat ~/.ssh/deploy_github.pub >> ~/.ssh/authorized_keys
cat ~/.ssh/deploy_github   # copiar completa y después: rm ~/.ssh/deploy_github
```

En GitHub → Settings → Secrets and variables → Actions → **New repository secret**:

| Secreto | Valor |
| --- | --- |
| `VM_HOST` | el dominio, por ejemplo `control-reactor.eastus.cloudapp.azure.com` |
| `VM_USER` | `reactor` |
| `VM_SSH_KEY` | la llave privada completa (incluidas las líneas `BEGIN` y `END`) |

Para probar sin esperar un merge: Actions → **Deploy** → Run workflow (rama `develop`).

## 4. Usar el juego desplegado

- **Celular o navegador:** abrir `https://<dominio>`. Con https el cliente llama a la API en
  `https://<dominio>/api` y al WebSocket en `wss://<dominio>/api/ws/...` (`client/src/config.py`).
- **PC (con el control físico):** desde `client/`:
  `$env:SERVER_URL="https://<dominio>/api"; $env:CONTROL_PUERTO="COM3"; python main.py`
- **Login con Google:** agregar `https://<dominio>/api/auth/google/callback` como URI de redirección
  en Google Cloud (ver `docs/google-oauth.md`).

## Operación

| Qué | Cómo |
| --- | --- |
| Ver logs | `docker compose -f docker-compose.prod.yml logs -f server` |
| Desplegar a mano | `cd ~/reactor && git pull && ./deploy/desplegar.sh` |
| Volver a una versión | `git reset --hard <commit> && ./deploy/desplegar.sh` |
| Entrar a la base | `docker compose -f docker-compose.prod.yml exec db psql -U reactor reactor` |

- **No borrar** los volúmenes `pgdata` (datos) ni `caddy_data` (certificados; Let's Encrypt limita
  cuántos se pueden emitir por semana).
- **Costo:** B1s + IP pública + disco cuesta unos pocos dólares al mes, dentro del crédito. Si la VM
  se detiene, el despliegue automático falla hasta encenderla de nuevo; el dominio no cambia.
- **Plan B:** si la nube falla el día de la demo, se juega en local con `docker compose up`.
