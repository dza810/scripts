
import pytest
from fastapi.testclient import TestClient
import json
from main import app, DB_FILE

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup: Create a clean database for each test
    with open(DB_FILE, "w") as f:
        json.dump([], f)
    yield
    # Teardown: Clean up the database file after each test
    with open(DB_FILE, "w") as f:
        json.dump([], f)

def test_create_customer():
    response = client.post("/customers", json={"name": "test user", "email": "test@example.com"})
    assert response.status_code == 200
    assert response.json() == {"name": "test user", "email": "test@example.com"}

    with open(DB_FILE, "r") as f:
        db_data = json.load(f)
    assert len(db_data) == 1
    assert db_data[0]["name"] == "test user"

def test_get_customers():
    # First, create a customer to ensure the database is not empty
    client.post("/customers", json={"name": "test user", "email": "test@example.com"})

    response = client.get("/customers")
    assert response.status_code == 200
    assert response.json() == [{"name": "test user", "email": "test@example.com"}]
