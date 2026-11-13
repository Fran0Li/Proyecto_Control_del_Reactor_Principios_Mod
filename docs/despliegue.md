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

## Lo que está desplegado

| Dato | Valor |
| --- | --- |
| URL | https://control-reactor.northcentralus.cloudapp.azure.com |
| Suscripción | Azure for Students (cuenta @estudiantec.cr de Francisco) |
| Grupo de recursos / VM | `rg-control-reactor` / `vm-reactor`, usuario `reactor` |
| Región | `northcentralus` (Azure for Students solo permite belgiumcentral, westus2, canadacentral, francecentral y northcentralus) |
| Tamaño | **Standard_B2ats_v2** (2 vCPU, 1 GB). B1s no tenía capacidad en la región; B2ats v2 también entra en las 750 h gratis |
| Disco | 64 GB Premium SSD (P6, incluido en lo gratis) |

## 1. Crear la VM (una sola vez, en Azure Cloud Shell con Bash)

Activar **Azure for Students** con la cuenta @estudiantec.cr (100 USD, sin tarjeta) y abrir
Cloud Shell (Bash, sin cuenta de almacenamiento):

```bash
# Regiones permitidas por la suscripción
az policy assignment list --query "[].parameters.listOfAllowedLocations.value" -o tsv

az group create -n rg-control-reactor -l northcentralus
az vm create -g rg-control-reactor -n vm-reactor --image Ubuntu2404 \
  --size Standard_B2ats_v2 --admin-username reactor --generate-ssh-keys \
  --public-ip-sku Standard --public-ip-address-dns-name control-reactor \
  --os-disk-size-gb 64 --storage-sku Premium_LRS
az vm open-port -g rg-control-reactor -n vm-reactor --port 80,443 --priority 900
```

Quedan abiertos solo 22, 80 y 443 (8000 y 5432 cerrados). Si el tamaño no está disponible
(`SkuNotAvailable`), probar otro de los gratuitos o otra región permitida.

Cloud Shell sin almacenamiento **pierde la llave SSH al cerrar la sesión**. Para volver a entrar
desde una sesión nueva:

```bash
[ -f ~/.ssh/id_rsa ] || ssh-keygen -q -t rsa -N '' -f ~/.ssh/id_rsa
az vm user update -g rg-control-reactor -n vm-reactor -u reactor --ssh-key-value "$(cat ~/.ssh/id_rsa.pub)"
ssh reactor@control-reactor.northcentralus.cloudapp.azure.com
```

## 2. Preparar la VM (una sola vez, por SSH)

```bash
ssh reactor@control-reactor.northcentralus.cloudapp.azure.com

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && exit   # volver a entrar para que tome el grupo

# 2 GB de swap: la VM tiene 1 GB de RAM y construir las imágenes la llena
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile
sudo swapon /swapfile && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Código y configuración
git clone -b develop https://github.com/Fran0Li/Proyecto_Control_del_Reactor_Principios_Mod ~/reactor
cd ~/reactor
# .env con claves aleatorias que nunca salen de la VM
PG=$(openssl rand -hex 24); JWT=$(openssl rand -hex 32)
sed -e "s#CAMBIAR_clave_larga#$PG#g" -e "s#CAMBIAR_openssl_rand_hex_32#$JWT#" deploy/.env.prod.example > .env
chmod 600 .env

./deploy/desplegar.sh
```

Revisar `https://control-reactor.northcentralus.cloudapp.azure.com/api/health/db` (debe decir `conectada`) y la raíz del dominio (cliente web).

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
| `VM_HOST` | el dominio, por ejemplo `control-reactor.northcentralus.cloudapp.azure.com` |
| `VM_USER` | `reactor` |
| `VM_SSH_KEY` | la llave privada completa (incluidas las líneas `BEGIN` y `END`) |

Para probar sin esperar un merge: Actions → **Deploy** → Run workflow (rama `develop`).

## 4. Usar el juego desplegado

- **Celular o navegador:** abrir `https://control-reactor.northcentralus.cloudapp.azure.com`. Con https el cliente llama a la API en
  `https://control-reactor.northcentralus.cloudapp.azure.com/api` y al WebSocket en `wss://control-reactor.northcentralus.cloudapp.azure.com/api/ws/...` (`client/src/config.py`).
- **PC (con el control físico):** desde `client/`:
  `$env:SERVER_URL="https://control-reactor.northcentralus.cloudapp.azure.com/api"; $env:CONTROL_PUERTO="COM3"; python main.py`
- **Login con Google:** agregar `https://control-reactor.northcentralus.cloudapp.azure.com/api/auth/google/callback` como URI de redirección
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
- **Costo:** VM B2ats v2 + IP pública + disco cuesta unos pocos dólares al mes, dentro del crédito. Si la VM
  se detiene, el despliegue automático falla hasta encenderla de nuevo; el dominio no cambia.
- **Plan B:** si la nube falla el día de la demo, se juega en local con `docker compose up`.

## Apagar o borrar al terminar el curso

- Pausar (deja de cobrar la VM, el dominio se mantiene): `az vm deallocate -g rg-control-reactor -n vm-reactor`
- Borrar todo (VM, disco, IP): `az group delete -n rg-control-reactor`
