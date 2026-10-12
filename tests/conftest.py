from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def pytest_addoption(parser):
    # This hook has to live in the root conftest. pytest only calls
    # pytest_addoption for "initial" conftests, so a copy under tests/e2e/ is
    # ignored whenever the run is driven by testpaths (a plain "pytest -q")
    # instead of an explicit tests/e2e path, and then every E2E test errors
    # out on the missing option.
    parser.addoption("--headed", action="store_true", help="Show the E2E browser window")


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "test-cars.db"


@pytest.fixture
def client(database_path: Path) -> Iterator[TestClient]:
    # The context manager runs FastAPI's lifespan, including table creation.
    # Each test gets a fresh on-disk database, never the real cars.db.
    with TestClient(create_app(database_path)) as test_client:
        yield test_client


@pytest.fixture
def car_payload() -> dict:
    return {"make": "Toyota", "model": "Corolla", "year": 2024, "color": "Silver"}
