# Credenciales de Google para el login (US-04)

El login con Google necesita un `GOOGLE_CLIENT_ID` y un `GOOGLE_CLIENT_SECRET` en el `.env`.
Sin ellos el resto del juego funciona igual; solo el botón de Google avisa que no está configurado.

## Crear las credenciales

Se crearon el 16/11/2026 con la cuenta de Google del proyecto (la misma del correo SMTP), en un
proyecto de Google Cloud llamado `control-del-reactor`. No hace falta facturación: **no** aceptar
la prueba gratuita de $300 que ofrece la consola, porque pide tarjeta.

1. Entrar a https://console.cloud.google.com con la cuenta del proyecto. En el selector de
   proyectos de arriba a la izquierda: **Proyecto nuevo** → `control-del-reactor`.
2. Con el proyecto seleccionado, abrir **Google Auth Platform** (antes "Pantalla de consentimiento
   de OAuth"): https://console.cloud.google.com/auth/overview → **Comenzar**.
   - Información de la app: nombre `Control del Reactor` y correo de asistencia.
   - Público: **Externo**.
   - Información de contacto: un correo del equipo.
3. **Público → Usuarios de prueba**: agregar los correos del equipo y del profesor. Mientras la app
   está "en prueba", solo esos correos pueden entrar.
4. **Clientes → Crear cliente** → tipo **Aplicación web**, nombre `Control del Reactor`. En
   **URI de redireccionamiento autorizados**, una por cada lugar donde corre el backend (es
   `URL_PUBLICA` + `/auth/google/callback`):

   ```
   http://localhost:8000/auth/google/callback
   https://control-reactor.northcentralus.cloudapp.azure.com/api/auth/google/callback
   ```

   En "Acceso a los datos" no hay que agregar nada: `openid` y `email` vienen por defecto.
5. Al crear el cliente, **descargar el JSON** (Google puede mostrar el secreto una sola vez).
   Guardarlo fuera de la carpeta del repositorio y copiar dos valores de adentro al `.env`, sin
   comillas:

   ```
   GOOGLE_CLIENT_ID=<"client_id" del JSON>.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=<"client_secret" del JSON, empieza con GOCSPX->
   ```

6. Reiniciar el backend: `docker compose up --force-recreate`.

El secreto **no** se sube al repo ni se pega en chats; cada quien lo pone en su `.env`.

### En la nube

En la VM (cómo entrar: `docs/despliegue.md`, sección 1), las mismas dos líneas en `~/reactor/.env`
y después:

```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate server
```

Para revisar la configuración **sin mostrar los valores**:

```bash
docker compose -f docker-compose.prod.yml exec -T server python -c "from app.core.config import settings as s; from app.services.google_oauth import crear_proveedor_google as g; i=s.google_client_id; k=s.google_client_secret; print('id ok:', i.endswith('.apps.googleusercontent.com'), '| secreto GOCSPX:', k.startswith('GOCSPX-'), '| configurado:', g().configurado, '| redirect:', g().redirect_uri)"
```

Debe dar todo `True` y el `redirect` igual a la segunda URI registrada en Google. Si
`/api/auth/google/iniciar` responde 503, el servidor no ve las credenciales; si Google responde
`redirect_uri_mismatch`, la URI registrada no coincide con `URL_PUBLICA`.

## Cómo funciona

1. En el login, "Entrar con Google" abre el navegador en `/auth/google/iniciar?sesion=<id>`.
2. El backend manda al jugador a Google y Google lo devuelve a `/auth/google/callback`.
3. El backend crea la cuenta, o la vincula si ya existía una con ese correo, y guarda el token.
4. El juego pregunta cada segundo por `/auth/google/resultado?sesion=<id>` y entra al lobby.

Si ya había una cuenta con ese correo que nunca se verificó, se vincula igual pero su contraseña
deja de servir: quien entra con Google es el dueño real del correo.
