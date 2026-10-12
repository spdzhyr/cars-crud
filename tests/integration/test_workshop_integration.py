"""Workshop tier 2: application code integrated with a real temporary SQLite file."""

import pytest

from app import database
from app.schemas import CarInput

pytestmark = pytest.mark.integration


def test_saved_car_can_be_read_from_sqlite(database_path):
    database.initialize(database_path)
    saved = database.create_car(
        database_path,
        CarInput(make="Toyota", model="Yaris", year=2020, color="Blue"),
    )
    loaded = database.get_car(database_path, saved.id)
    assert loaded is not None
    assert loaded.id == saved.id
    assert loaded.make == "Toyota"
    assert loaded.year == 2020


def test_deleting_one_car_keeps_the_other(database_path):
    database.initialize(database_path)
    first = database.create_car(
        database_path,
        CarInput(make="Ford", model="Focus", year=2015, color="Red"),
    )
    second = database.create_car(
        database_path,
        CarInput(make="Honda", model="Civic", year=2019, color="Blue"),
    )

    assert database.delete_car(database_path, first.id) is True

    # The deleted row is gone...
    assert database.get_car(database_path, first.id) is None
    # ...and the untouched row is still complete.
    assert database.get_car(database_path, second.id) == second

    remaining = database.list_cars(database_path)
    assert len(remaining) == 1
    assert remaining == [second]
