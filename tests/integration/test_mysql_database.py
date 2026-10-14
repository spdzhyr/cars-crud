"""MySQL backend integration test.

The workshop guide notes that the existing unit, integration and API tests all
run against temporary SQLite files, so nothing exercises ``app.mysql_database``.
This file covers that gap.

It connects to the MySQL service started by ``docker compose up -d``, using the
same four environment variables the Compose file passes to the ``app`` service.
When no MySQL server is reachable the whole module is skipped, which keeps a
plain ``pytest -q`` green on a machine that only has the SQLite setup.

The application's MySQL user is deliberately not allowed to create databases, so
this test uses the existing database and empties the ``cars`` table around each
test instead. That is exactly the shape the SQLite integration tests have, only
against a server database.

Run it against the Compose database with, for example::

    docker compose cp tests/integration/test_mysql_database.py app:/tmp/test_mysql_database.py
    docker compose exec -e PYTHONPATH=/tmp/pylibs app \\
        python -m pytest /tmp/test_mysql_database.py -q -p no:cacheprovider
"""

import os

import pytest

from app import mysql_database
from app.schemas import CarInput

pytestmark = pytest.mark.integration


def _connection_kwargs(database: str | None = None) -> dict:
    kwargs = {
        "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", ""),
        "password": os.environ.get("MYSQL_PASSWORD", ""),
        "charset": "utf8mb4",
        "autocommit": True,
        "connect_timeout": 10,
    }
    if database is not None:
        kwargs["database"] = database
    return kwargs


def _connect(database: str | None = None):
    import pymysql

    return pymysql.connect(**_connection_kwargs(database))


@pytest.fixture(scope="module", autouse=True)
def mysql_available() -> None:
    """Skip the module when MySQL or its configuration is missing."""
    if not os.environ.get("MYSQL_USER") or not os.environ.get("MYSQL_PASSWORD"):
        pytest.skip("MySQL credentials are not configured in the environment")

    try:
        import pymysql  # noqa: F401
    except ImportError:  # pragma: no cover - only without the MySQL driver
        pytest.skip("PyMySQL is not installed")

    try:
        connection = mysql_database.connect()
    except Exception as error:  # noqa: BLE001 - any driver/network failure means skip
        pytest.skip(f"MySQL is not reachable: {error}")
    else:
        connection.close()


@pytest.fixture(autouse=True)
def empty_cars_table(mysql_available) -> None:
    """Leave the table empty before and after each test in this module."""
    mysql_database.initialize(None)
    _truncate()
    yield
    _truncate()


def _truncate() -> None:
    connection = _connect(os.environ["MYSQL_DATABASE"])
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM cars")
    finally:
        connection.close()


def test_crud_against_mysql():
    """The same six operations the SQLite module offers, against real MySQL."""
    assert mysql_database.list_cars(None) == []

    created = mysql_database.create_car(
        None, CarInput(make="Toyota", model="Corolla", year=2024, color="Silver")
    )
    assert created.id > 0
    assert mysql_database.get_car(None, created.id) == created

    updated = mysql_database.update_car(
        None, created.id, CarInput(make="Honda", model="Civic", year=2025)
    )
    assert updated.id == created.id
    assert mysql_database.get_car(None, created.id).model == "Civic"
    # Omitting color resets it, exactly like the SQLite backend.
    assert mysql_database.get_car(None, created.id).color == ""

    assert mysql_database.delete_car(None, created.id) is True
    assert mysql_database.get_car(None, created.id) is None


def test_missing_car_operations_report_absent():
    assert mysql_database.get_car(None, 999999) is None
    assert (
        mysql_database.update_car(
            None, 999999, CarInput(make="Honda", model="Civic", year=2025)
        )
        is None
    )
    assert mysql_database.delete_car(None, 999999) is False


def test_list_returns_newest_first():
    first = mysql_database.create_car(None, CarInput(make="A", model="One", year=2000))
    second = mysql_database.create_car(None, CarInput(make="B", model="Two", year=2001))

    assert [car.id for car in mysql_database.list_cars(None)] == [second.id, first.id]


def _insert_expecting_check_violation(values: tuple) -> None:
    """Insert raw SQL and expect MySQL to reject it via a CHECK constraint.

    MySQL reports a CHECK violation as error 3819, which PyMySQL surfaces as an
    OperationalError. Asserting the SQLSTATE/errno keeps this honest: a
    programming mistake such as a bad column name would not be swallowed.
    """
    import pymysql

    connection = _connect(os.environ["MYSQL_DATABASE"])
    try:
        with connection.cursor() as cursor:
            with pytest.raises(pymysql.err.OperationalError) as caught:
                cursor.execute(
                    "INSERT INTO cars (make, model, year, color) VALUES (%s, %s, %s, %s)",
                    values,
                )
            assert caught.value.args[0] == 3819
            assert "Check constraint" in caught.value.args[1]
    finally:
        connection.close()


def test_mysql_enforces_its_own_year_constraint():
    """MySQL has its own CHECK constraint; this is not only Pydantic validation."""
    _insert_expecting_check_violation(("Bad", "Row", 1800, ""))


def test_mysql_rejects_a_blank_make():
    """The valid_make CHECK constraint rejects whitespace-only values."""
    _insert_expecting_check_violation(("   ", "Row", 2020, ""))
