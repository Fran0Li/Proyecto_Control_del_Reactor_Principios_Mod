# Credenciales de Google para el login (US-04)

El login con Google necesita un `GOOGLE_CLIENT_ID` y un `GOOGLE_CLIENT_SECRET` en el `.env`.
Sin ellos el resto del juego funciona igual; solo el botón de Google avisa que no está configurado.

## Crear las credenciales

1. Entrar a https://console.cloud.google.com con una cuenta de Google y crear un proyecto
   (por ejemplo `control-del-reactor`).
2. **APIs y servicios → Pantalla de consentimiento de OAuth**
   - Tipo de usuario: **Externo**.
   - Nombre de la app: `Control del Reactor`, correo de soporte y correo del desarrollador.
   - Permisos: `openid` y `.../auth/userinfo.email`.
   - En **Usuarios de prueba** agregar los correos del equipo y del profesor. Mientras la app
     está "en prueba", solo esos correos pueden entrar.
3. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth**
   - Tipo de aplicación: **Aplicación web**.
   - URI de redireccionamiento autorizado: `http://localhost:8000/auth/google/callback`
     (si el backend está en otra dirección, la misma ruta con esa dirección, igual que
     `URL_PUBLICA` en el `.env`).
4. Copiar el ID de cliente y el secreto al `.env`:

   ```
   GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=xxxx
   ```

5. Reiniciar el backend: `docker compose up --build`.

El secreto **no** se sube al repo; cada quien lo pone en su `.env`.

## Cómo funciona

1. En el login, "Entrar con Google" abre el navegador en `/auth/google/iniciar?sesion=<id>`.
2. El backend manda al jugador a Google y Google lo devuelve a `/auth/google/callback`.
3. El backend crea la cuenta, o la vincula si ya existía una con ese correo, y guarda el token.
4. El juego pregunta cada segundo por `/auth/google/resultado?sesion=<id>` y entra al lobby.

Si ya había una cuenta con ese correo que nunca se verificó, se vincula igual pero su contraseña
deja de servir: quien entra con Google es el dueño real del correo.
