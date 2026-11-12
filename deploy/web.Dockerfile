# Imagen del servicio web: compila el cliente con pygbag y lo sirve con Caddy.
# Se construye desde la raíz del repo: docker compose -f docker-compose.prod.yml build web

# 1. Compilar el cliente pygame a WebAssembly (queda en build/web: index.html + client.apk)
FROM python:3.12-slim AS cliente
RUN pip install --no-cache-dir pygbag==0.9.3
WORKDIR /compilar/client
COPY client/ .
# Las pruebas no hacen falta en el navegador; así el paquete pesa menos
RUN rm -rf tests && python -m pygbag --build .

# 2. Caddy: HTTPS automático, proxy a la API y archivos del cliente
FROM caddy:2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=cliente /compilar/client/build/web /srv
