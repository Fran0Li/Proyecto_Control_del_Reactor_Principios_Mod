import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.session import Base


@pytest.fixture()
def db_session():
    url = os.getenv("TEST_DATABASE_URL", "sqlite://")
    opciones = {}
    if url.startswith("sqlite"):
        # TestClient atiende cada petición en otro hilo: hay que compartir la conexión
        opciones = {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    engine = create_engine(url, **opciones)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()