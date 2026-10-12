"""Workshop tier 1: isolated validation, without a server or database."""

import pytest
from pydantic import ValidationError

from app.schemas import CarInput

pytestmark = pytest.mark.unit


def test_car_text_fields_are_trimmed():
    car = CarInput(
        make="  Mazda  ",
        model="  MX-5  ",
        year=2020,
        color="  Red  ",
    )
    assert car.make == "Mazda"
    assert car.model == "MX-5"
    assert car.color == "Red"


def test_blank_model_is_rejected():
    # A single space must not become a valid one-character model name.
    with pytest.raises(ValidationError):
        CarInput(make="Mazda", model=" ", year=2020)
