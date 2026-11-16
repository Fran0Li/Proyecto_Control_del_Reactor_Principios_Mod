FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Las mismas versiones exactas que prueba el CI (docs/dependencias.md)
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

COPY app ./app
# Migraciones: se aplican al arrancar, así una base nueva queda con todas las tablas
COPY alembic.ini .
COPY alembic ./alembic

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
