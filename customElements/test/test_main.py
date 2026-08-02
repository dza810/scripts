import sqlite3

import pytest
from fastapi.testclient import TestClient

from proj import setupSqlite
from proj.main import *

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


def test_dict_factory(db_connection):
    con = db_connection
    con.execute("""
        CREATE TABLE test_dict_factory(
            test_id integer PRIMARY KEY autoincrement,
            uk_num1 integer,
            uk_text1 text,
            uk_bool1 bool,
            text2 text,
            unique (uk_num1, uk_text1, uk_bool1)
        )
    """)
    con.execute("""
        INSERT INTO test_dict_factory(uk_num1, uk_text1, uk_bool1, text2) 
        VALUES (1, 'a', '1', 'abc')
    """)
    con.execute("""
        INSERT INTO test_dict_factory(uk_num1, uk_text1, uk_bool1, text2) 
        VALUES (2, 'b', '0', 'xyz')
    """)
    con.row_factory = dict_factory
    result = con.execute("SELECT * FROM test_dict_factory ORDER BY rowid").fetchall()

    assert result[0]["test_id"] == 1
    assert result[0]["uk_num1"] == 1
    assert result[0]["uk_text1"] == "a"
    assert result[0]["uk_bool1"] == 1
    assert result[0]["text2"] == "abc"

    assert result[1]["test_id"] == 2
    assert result[1]["uk_num1"] == 2
    assert result[1]["uk_text1"] == "b"
    assert result[1]["uk_bool1"] == 0
    assert result[1]["text2"] == "xyz"

def test_handleSqlValue():
    tests = [
        { 'i': 1, 'o': '1'},
        { 'i': 1.2, 'o': '1.2'},
        { 'i': None, 'o': 'NULL'},
        { 'i': True, 'o': '1'},
        { 'i': False, 'o': '0'},
    ]
    for test in  tests:
        i = test['i']
        o = test['o']
        assert handleSqlValue(i) == o

def test_insert(db_connection):
    con = db_connection
    data = {
        "uk_num1": 1,
        "uk_text1": 'a',
        "uk_bool1": 0,
        "text2": "'; delete test",
    }
    cur = insert(con, "test", data)
    assert cur is not None
    rowid = cur.lastrowid
    result = con.execute("SELECT * FROM test ORDER BY rowid").fetchall()
    assert len(result) == 1
    assert result[0] == data | { 'test_id': rowid }

def test_update(db_connection):
    test_id = 1
    insert_data = [
        {
            "test_id": test_id,
            "uk_num1": 1,
            "uk_text1": 'a',
            "uk_bool1": 0,
            "text2": "xxxx",
        }, {
            "uk_num1": 2,
            "uk_text1": 'a',
            "uk_bool1": 0,
            "text2": "'; delete test",
        }
    ]
    update_data = {
        "uk_num1": 99,
        "uk_text1": 'abc',
        "uk_bool1": 1,
        "text2": "'; delete from test;",
    }
    for d in insert_data:
        insert(db_connection, "test", d)
    update(db_connection, "test", update_data, {'test_id': 1} )
    result = db_connection.execute("SELECT * FROM test ORDER BY rowid").fetchall()
    assert len(result) == 2
    assert result[0] == update_data | { 'test_id': 1 }
    assert result[1] == insert_data[1] | {'test_id': 2}


def test_getClass(db_connection_with_tables):
    con = db_connection_with_tables
    cur = insert(con, "class_master", {
        "class_cd": 'testclass',
        "class_name": 'テスト区分',
    })
    assert cur is not None
    class_id = cur.lastrowid
    data = [
        {
            'class_id': class_id,
            'class_dtl_cd': 'testclass_1',
            'class_dtl_name': 'テストクラス1',
            'view_order': 10
        },
        {
            'class_id': class_id,
            'class_dtl_cd': 'testclass_2',
            'class_dtl_name': 'テストクラス2',
            'view_order': 9
        },
        {
            'class_id': class_id,
            'class_dtl_cd': 'xxx',
            'class_dtl_name': 'yyy',
            'view_order': 8
        },
    ]
    for d in data:
        insert(con, "class_dtl_master", d)

    result = getClass(con, "testclass")
    assert result == [
            {'value': 'xxx', 'name': 'yyy'},
            {'value': 'testclass_2', 'name': 'テストクラス2'},
            {'value': 'testclass_1', 'name': 'テストクラス1'},
    ]

@pytest.mark.parametrize("table,screenCd", [
    ("screen","screen_master"),
    ("column","column_master"),
])
def test_screenCls_search_zero(db_connection_with_tables, screenCd, table):
    con = db_connection_with_tables
    con.execute(f"delete from {table}")
    con.commit()
    screen = get_screen(screenCd, con)
    assert screen.search({}) == []

def test_screenCls_search_one_by_id(db_connection_with_tables):
    con = db_connection_with_tables
    screen = get_screen("screen_master", con)
    assert len(screen.search({'screen_cd': "screen_master"})) == 1

def test_screenCls_search_invalid_key(db_connection_with_tables):
    con = db_connection_with_tables
    screen = get_screen("screen_master", con)
    with pytest.raises(InvalidKeyException):
        screen.search({'xxx': "abc"})


def test_insert_empty_data(db_connection):
    assert insert(db_connection, "test", {}) is None

def test_update_empty_data(db_connection):
    assert update(db_connection, "test", {}, {"test_id": 1}) is None


@pytest.mark.parametrize("condition_cd,value,expected", [
    ("equal", 15, [("`price` = ?", "15")]),
    ("equal", None, [("`price` is NULL", None)]),
    ("lesser_than_or_equal", 15, [("`price` <= ?", "15")]),
    ("greater_than_or_equal", 15, [("? <= `price`", "15")]),
    ("between", {"from": 10, "to": 20}, [("`price` >= ?", "10"), ("`price` <= ?", "20")]),
    ("between", {"from": 10}, [("`price` >= ?", "10")]),
    ("between", {"to": 20}, [("`price` <= ?", "20")]),
    ("between", {}, []),
    ("contains", "aa bb", [
        ("`price` like ('%' || ? || '%')", "aa"),
        ("`price` like ('%' || ? || '%')", "bb"),
    ]),
    ("unknown_condition", 15, []),
])
def test_make_condition_query(db_connection_with_tables, condition_cd, value, expected):
    screen = get_screen("car_list", db_connection_with_tables)
    option = {"column_cd": "price", "condition_cd": condition_cd}
    assert screen.make_condition_query(option, "price", value) == expected


def test_make_condition(db_connection_with_tables):
    screen = get_screen("car_list", db_connection_with_tables)
    assert screen.make_condition({"model": "Focus"}) == [("`model` = ?", "Focus")]

def test_make_condition_multiple(db_connection_with_tables):
    screen = get_screen("car_list", db_connection_with_tables)
    assert screen.make_condition({"model": "Focus", "make": "cdFord"}) == [("`model` = ?", "Focus"), ("`make` = ?", "cdFord")]

def test_make_condition_invalid_key(db_connection_with_tables):
    screen = get_screen("car_list", db_connection_with_tables)
    with pytest.raises(InvalidKeyException):
        screen.make_condition({"bogus_key": 1})


def test_run_search_with_condition(db_connection_with_tables):
    con = db_connection_with_tables
    insert(con, "car", {"make": "Tesla", "model": "Model 3", "price": 50000, "electric": 1})
    insert(con, "car", {"make": "Ford", "model": "Focus", "price": 30000, "electric": 0})
    screen = get_screen("car_list", con)
    result = screen.search({"model": "Focus"})
    assert len(result) == 1
    assert result[0]["model"] == "Focus"
    assert result[0]["make"] == "Ford"


def test_run_insert_invalid_key(db_connection_with_tables):
    con = db_connection_with_tables
    screen = get_screen("car_list", con)
    with pytest.raises(InvalidKeyException):
        screen.run_insert("car", {"bogus_key": 1})


def test_run_update_invalid_key(db_connection_with_tables):
    con = db_connection_with_tables
    screen = get_screen("car_list", con)
    with pytest.raises(InvalidKeyException):
        screen.run_update("car", {"bogus_key": 1}, {"car_id": 1})


def test_register_insert_and_update(db_connection_with_tables):
    con = db_connection_with_tables
    screen = get_screen("car_list", con)
    screen.update(Register(
        insertList=[
            {"make": "Tesla", "model": "Model 3", "price": 50000, "electric": 1},
            {"make": "Ford", "model": "Focus", "price": 30000, "electric": 0},
        ],
        deleteList=[],
        updateList=[],
    ))
    rows = con.execute("SELECT * FROM car ORDER BY car_id").fetchall()
    assert len(rows) == 2

    row = screen.search({"make": "Ford"})[0]
    screen.update(Register(
        insertList=[],
        deleteList=[],
        updateList=[{"id": row["id"], "price": 33333}],
    ))
    updated = con.execute("SELECT * FROM car WHERE make='Ford'").fetchone()
    assert updated["price"] == 33333


def test_register_invalid_insert_key(db_connection_with_tables):
    con = db_connection_with_tables
    screen = get_screen("car_list", con)
    with pytest.raises(InvalidKeyException):
        screen.update(Register(
            insertList=[{"make": "Tesla", "model": "Model 3", "bogus_key": 1}],
            deleteList=[],
            updateList=[],
        ))


def test_register_delete(db_connection_with_tables):
    con = db_connection_with_tables
    screen = get_screen("car_list", con)
    screen.update(Register(
        insertList=[
            {"make": "Tesla", "model": "Model 3", "price": 50000, "electric": 1},
            {"make": "Ford", "model": "Focus", "price": 30000, "electric": 0},
        ],
        deleteList=[],
        updateList=[],
    ))
    rows = con.execute("SELECT * FROM car ORDER BY car_id").fetchall()
    assert len(rows) == 2

    target = screen.search({"make": "Ford"})[0]
    screen.update(Register(
        insertList=[],
        deleteList=[target["id"]],
        updateList=[],
    ))
    remaining = con.execute("SELECT * FROM car").fetchall()
    assert len(remaining) == 1
    assert remaining[0]["make"] == "Tesla"


def test_getColumnOptions(db_connection_with_tables):
    con = db_connection_with_tables
    screen = get_screen("car_list", con)
    options = screen.getColumnOptions()
    assert [c["column_cd"] for c in options] == ["make", "model", "price", "electric"]
    assert options[0]["type"] == "dropdown"


def test_getSearchForm(db_connection_with_tables):
    con = db_connection_with_tables
    screen = get_screen("car_list", con)
    forms = screen.getSearchForm()
    assert [(f["search_form_cd"], f["condition_cd"]) for f in forms] == [
        ("make", "equal"),
        ("model", "equal"),
        ("price", "equal"),
        ("electric", "equal"),
    ]


def test_getRowStyle_empty(db_connection_with_tables):
    con = db_connection_with_tables
    screen = get_screen("car_list", con)
    assert screen.getRowStyle() == []


def test_getRowStyle(db_connection_with_tables):
    con = db_connection_with_tables
    screen = get_screen("row_style_master", con)
    assert screen.getRowStyle() == [{"code": None, "style": None}]


@pytest.mark.parametrize("screen_cd,expected_cls", [
    ("screen_master", ScreenMaster),
    ("column_master", ColumnMaster),
    ("car_list", CarList),
    ("class_master", ClassMaster),
    ("class_dtl_master", ClassDtlMaster),
    ("search_form_master", SearchFormMaster),
    ("row_style_master", RowStyleMaster),
])
def test_get_screen(db_connection_with_tables, screen_cd, expected_cls):
    con = db_connection_with_tables
    screen = get_screen(screen_cd, con)
    assert isinstance(screen, expected_cls)


def test_get_screen_invalid(db_connection_with_tables):
    con = db_connection_with_tables
    with pytest.raises(InvalidScreenException):
        get_screen("no_such_screen", con)


def test_api_root(api_client):
    r = api_client.get("/")
    assert r.status_code == 200


def test_api_search(api_client):
    r = api_client.post("/search?screenCd=car_list", json={"params": {}})
    assert r.status_code == 200
    assert r.json() == []


def test_api_search_with_params(api_client):
    api_client.post("/register?screenCd=car_list", json={
        "insertList": [{"make": "Tesla", "model": "Model 3", "price": 50000, "electric": 1}],
        "deleteList": [],
        "updateList": [],
    })
    r = api_client.post("/search?screenCd=car_list", json={"params": {"make": "Tesla"}})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["model"] == "Model 3"


def test_api_search_invalid_key_returns_418(api_client):
    r = api_client.post("/search?screenCd=car_list", json={"params": {"bogus_key": 1}})
    assert r.status_code == 418
    assert r.json() == {"message": "invalid key: bogus_key"}


def test_api_register_insert(api_client):
    r = api_client.post("/register?screenCd=car_list", json={
        "insertList": [{"make": "Tesla", "model": "Model 3", "price": 50000, "electric": 1}],
        "deleteList": [],
        "updateList": [],
    })
    assert r.status_code == 200
    r = api_client.post("/search?screenCd=car_list", json={"params": {}})
    assert len(r.json()) == 1


def test_api_getClass(api_client):
    r = api_client.get("/getClass", params={"code": "make"})
    assert r.status_code == 200
    assert r.json() == [
        {"value": "cdFord", "name": "Ford"},
        {"value": "cdTesla", "name": "Tesla"},
        {"value": "cdToyota", "name": "Toyota"},
    ]


def test_api_getColumns(api_client):
    r = api_client.get("/getColumns", params={"screenCd": "car_list"})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"columnOptions", "rowStyles"}
    make = next(c for c in body["columnOptions"] if c["column_cd"] == "make")
    assert make["type"] == "dropdown"
    assert make["classes"] == [
        {"value": "cdFord", "name": "Ford"},
        {"value": "cdTesla", "name": "Tesla"},
        {"value": "cdToyota", "name": "Toyota"},
    ]


def test_api_getSearchForms(api_client):
    r = api_client.get("/getSearchForms", params={"screenCd": "car_list"})
    assert r.status_code == 200
    assert [f["search_form_cd"] for f in r.json()] == ["make", "model", "price", "electric"]

