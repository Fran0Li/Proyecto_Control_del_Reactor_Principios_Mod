# Versiones de las dependencias

Acción de la retrospectiva del Sprint 2: el CI se rompió el 21/10 porque `ubuntu-latest` cambió de
versión sin que nadie tocara el código. Lo mismo puede pasar con cualquier dependencia que no esté
fija. Por eso el CI y la imagen de producción usan **versiones exactas** de todo.

## Qué está fijo y dónde

| Qué | Dónde | Versión |
| --- | --- | --- |
| Runner del CI | `.github/workflows/ci.yml` | `ubuntu-24.04` |
| Acciones de GitHub | `.github/workflows/ci.yml` | `checkout@v4.4.0`, `setup-python@v5.6.0`, `compile-sketches@v1.1.4` |
| Core de Arduino | `.github/workflows/ci.yml` | `arduino:avr` 1.8.8, la misma que instala el Arduino IDE 2.3 |
| Dependencias del backend, también las indirectas | `server/constraints.txt` | Las usa el CI y la imagen Docker |
| Dependencias del cliente para el CI | `client/constraints.txt` | Las usa el CI |
| Herramientas de pruebas y lint | `server/requirements-dev.txt`, `client/requirements-dev.txt` | `pytest==8.4.2`, `ruff==0.8.6` |
| pygbag (cliente web) | `deploy/web.Dockerfile` | 0.9.3 |

## Por qué hay dos archivos por carpeta

- **`requirements.txt`** dice qué necesita el proyecto, con rangos compatibles (`fastapi==0.115.*`).
  Es lo que instala cada integrante en su PC, sea cual sea su versión de Python o su sistema.
- **`constraints.txt`** fija la versión exacta de cada paquete, incluidos los que se instalan de
  rebote (por ejemplo `starlette`, que viene con FastAPI). El CI y el Docker instalan con
  `pip install -r requirements.txt -c constraints.txt`, así lo que se prueba es exactamente lo que
  se despliega.

`ruff` está fijo también en `requirements-dev.txt` porque dos versiones distintas pueden marcar
errores distintos: si en tu PC pasa el lint, en el CI también tiene que pasar.

## Cómo actualizar una versión

Se hace a propósito, en un PR aparte, nunca de rebote dentro de otra historia.

1. Cambiar el rango en `requirements.txt` o `requirements-dev.txt` si hace falta.
2. Regenerar el archivo de versiones exactas, en la carpeta `server/` o `client/`:

   ```
   pip install uv
   uv pip compile requirements-dev.txt --python-version 3.12 --python-platform x86_64-manylinux_2_28 --no-annotate -o constraints.txt
   ```

   Se resuelve para Python 3.12 en Linux, que es lo que usan el CI y la imagen, aunque lo corras en
   Windows.
3. Correr las pruebas y abrir el PR. El CI confirma que todo funciona con las versiones nuevas.

Para las acciones de GitHub y el core de Arduino, cambiar la versión directamente en `ci.yml`.

## Lo que no se fijó, a propósito

| Qué | Por qué |
| --- | --- |
| `postgres:16` (servicio del CI y Compose) | Las versiones menores de PostgreSQL solo traen correcciones y son compatibles con los datos; la mayor sí está fija |
| `python:3.12-slim` y `caddy:2-alpine` (imágenes base) | Reciben parches de seguridad; la versión menor de Python y la mayor de Caddy sí están fijas |
| `python-version: "3.12"` en el CI | Igual que la imagen: los parches de Python no cambian el comportamiento |
