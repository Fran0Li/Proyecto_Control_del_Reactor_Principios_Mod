#!/usr/bin/env bash
# Levanta en la VM la versión que está en la carpeta. El workflow de entrega continua
# (.github/workflows/deploy.yml) primero deja el repo en el commit que pasó el CI y luego llama
# este script por SSH. A mano, en la VM:
#   cd ~/reactor && git pull && ./deploy/desplegar.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Desplegando $(git log -1 --format='%h %s')"
docker compose -f docker-compose.prod.yml up -d --build --remove-orphans
# Borra las imágenes viejas: el disco de la VM es pequeño
docker image prune -f
docker compose -f docker-compose.prod.yml ps
