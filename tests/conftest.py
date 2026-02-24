from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.db.base import Base
from app.main import create_app


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    # Use a temp SQLite DB for tests
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    test_db_url = f"sqlite:///{path}"

    engine = create_engine(test_db_url, future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    app = create_app()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    try:
        os.remove(path)
    except OSError:
        pass