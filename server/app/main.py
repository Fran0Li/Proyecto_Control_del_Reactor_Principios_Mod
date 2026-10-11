"""Punto de entrada del backend de Control del Reactor."""

from fastapi import FastAPI

from app.api.routes import auth, health, partidas

app = FastAPI(
    title="Control del Reactor API",
    description="Backend del juego: autenticación, partidas, ranking y tiempo real.",
    version="0.1.0",
)
app.include_router(auth.router)  # Rol A: US-01 a US-06
app.include_router(partidas.router)
app.include_router(health.router)
