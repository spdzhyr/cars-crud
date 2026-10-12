"""Workshop API tier: the HTTP contract through TestClient and a real test database."""

import pytest

pytestmark = pytest.mark.api


def test_post_car_returns_201_and_json(client):
    payload = {
        "make": "Ford",
        "model": "Fiesta",
        "year": 2018,
        "color": "Black",
    }
    response = client.post("/api/cars", json=payload)
    assert response.status_code == 201
    car = response.json()
    assert car["id"] > 0
    assert car["make"] == "Ford"
    assert car["model"] == "Fiesta"
    assert response.headers["location"] == f"/api/cars/{car['id']}"


def test_invalid_year_is_not_saved(client):
    payload = {
        "make": "Ford",
        "model": "Fiesta",
        "year": 1800,  # below the 1886 lower bound
        "color": "Black",
    }
    response = client.post("/api/cars", json=payload)
    assert response.status_code == 422

    # The rejected request must not leave anything behind.
    listed = client.get("/api/cars")
    assert listed.status_code == 200
    assert listed.json() == []
