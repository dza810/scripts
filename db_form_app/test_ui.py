
from fastapi.testclient import TestClient
import pytest
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

def test_root_page_loads_successfully():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_root_page_renders_existing_customers():
    # Setup: Create a customer
    customer_data = {"name": "John Doe", "email": "john@doe.com"}
    with open(DB_FILE, "w") as f:
        json.dump([customer_data], f)

    # Action
    response = client.get("/")

    # Assert
    assert response.status_code == 200
    assert "John Doe" in response.text
    assert "john@doe.com" in response.text
