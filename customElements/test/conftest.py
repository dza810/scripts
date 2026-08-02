import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from proj import setup_sqlite
from proj.db import dict_factory, get_connection_sync, insert
from proj.main import app, get_connection


class CsrfTestClient(TestClient):
    def _ensure_csrf(self) -> None:
        if self.cookies.get("csrftoken") is None:
            resp = TestClient.request(self, "GET", "/getCsrfToken")
            assert resp.status_code == 200

    def request(self, method: str, url: str, **kwargs):
        self._ensure_csrf()
        headers = kwargs.get("headers")
        if headers is None:
            headers = {}
            kwargs["headers"] = headers
        headers.setdefault("csrftoken", self.cookies.get("csrftoken"))
        return super().request(method, url, **kwargs)


client: TestClient = CsrfTestClient(app)
plain_client: TestClient = TestClient(app)


@pytest.fixture(scope="function")
def db_connection() -> Iterator[sqlite3.Connection]:
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
def db_connection_with_tables(
    db_connection: sqlite3.Connection,
) -> sqlite3.Connection:
    setup_sqlite.setup(db_connection)
    return db_connection


@pytest.fixture(scope="function")
def insert_cars(db_connection_with_tables: sqlite3.Connection) -> sqlite3.Connection:
    insert(
        db_connection_with_tables,
        "car",
        {
            "make": "Tesla",
            "model": "Model 3",
            "price": 50000,
            "electric": 1,
        },
    )
    insert(
        db_connection_with_tables,
        "car",
        {
            "make": "Ford",
            "model": "Focus",
            "price": 30000,
            "electric": 0,
        },
    )
    return db_connection_with_tables


@pytest.fixture(scope="function")
def api_client() -> Iterator[TestClient]:
    with _api_db():
        yield client


@pytest.fixture(scope="function")
def api_client_no_csrf() -> Iterator[TestClient]:
    with _api_db():
        yield plain_client


@contextmanager
def _api_db() -> Iterator[None]:
    with sqlite3.connect(":memory:", check_same_thread=False) as con:
        con.row_factory = dict_factory
        con.autocommit = False
        setup_sqlite.setup(con)

        def override_get_connection() -> Iterator[sqlite3.Connection]:
            yield con

        app.dependency_overrides[get_connection] = override_get_connection
        try:
            yield
        finally:
            app.dependency_overrides.clear()
