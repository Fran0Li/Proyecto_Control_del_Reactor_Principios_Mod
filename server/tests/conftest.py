import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.session import Base


@pytest.fixture()
def db_session():
    url = os.getenv("TEST_DATABASE_URL", "sqlite://")
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()