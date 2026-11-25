"""Cierra las partidas que quedaron en espera o en curso de la ejecución anterior.

Corre al arrancar el contenedor del servidor, antes de uvicorn (Dockerfile y docker compose):
los motores de las partidas viven en memoria, así que después de reiniciar (por ejemplo, con
cada despliegue) ninguna partida vieja puede continuar.

    python -m app.scripts.cerrar_partidas_activas
"""

from app.db.session import SessionLocal
from app.repositories.partida_repository import PartidaRepository


def main() -> int:
    with SessionLocal() as sesion:
        cerradas = PartidaRepository(sesion).cerrar_activas()
    print(f"Partidas activas de la ejecución anterior cerradas: {cerradas}")
    return cerradas


if __name__ == "__main__":
    main()
