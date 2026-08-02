import sqlite3

import pytest
from fastapi.testclient import TestClient

from proj import setupSqlite
from proj.db import dict_factory, get_connection_sync, insert
from proj.main import app, get_connection

client = TestClient(app)


@pytest.fixture(scope="function")
def db_connection():
    for con in get_connection_sync(":memory:"):
        con.execute("""
            CREATE TABLE test(
                test_id integer PRIMARY KEY autoincrement,
                uk_num1 integer,
                uk_text1 text,
                uk_bool1 bool,
                text2 text,
                unique (uk_num1, uk_text1, uk_bool1)
            )
        """)
        yield con


@pytest.fixture(scope="function")
def db_connection_with_tables(db_connection):
    setupSqlite.setup(db_connection)
    return db_connection


@pytest.fixture(scope="function")
def insert_cars(db_connection_with_tables):
    insert(db_connection_with_tables, "car", {
        "make": "Tesla", "model": "Model 3", "price": 50000, "electric": 1,
    })
    insert(db_connection_with_tables, "car", {
        "make": "Ford", "model": "Focus", "price": 30000, "electric": 0,
    })
    return db_connection_with_tables


@pytest.fixture(scope="function")
def api_client():
    with sqlite3.connect(":memory:", check_same_thread=False) as con:
        con.row_factory = dict_factory
        con.autocommit = False
        setupSqlite.setup(con)

        def override_get_connection():
            yield con

        app.dependency_overrides[get_connection] = override_get_connection
        yield client
        app.dependency_overrides.clear()
