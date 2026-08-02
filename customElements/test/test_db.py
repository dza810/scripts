import sqlite3

import pytest

from proj.db import (
    delete,
    dict_factory,
    getClass,
    handleSqlValue,
    insert,
    makeEqCondition,
    quote_ident,
    select,
    update,
)


def test_dict_factory(db_connection: sqlite3.Connection) -> None:
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


def test_handleSqlValue() -> None:
    tests = [
        {"i": 1, "o": "1"},
        {"i": 1.2, "o": "1.2"},
        {"i": None, "o": "NULL"},
        {"i": True, "o": "1"},
        {"i": False, "o": "0"},
    ]
    for test in tests:
        i = test["i"]
        o = test["o"]
        assert handleSqlValue(i) == o


def test_quote_ident() -> None:
    assert quote_ident("price") == "`price`"
    assert quote_ident("make` FROM car --") == "`make`` FROM car --`"
    assert quote_ident("a``b") == "`a````b`"


def test_make_eq_condition_backtick_escaped() -> None:
    cond, param = makeEqCondition("make` FROM car --", "x")
    assert cond == "`make`` FROM car --` = ?"
    assert param == "x"


def test_insert(db_connection: sqlite3.Connection) -> None:
    con = db_connection
    data = {
        "uk_num1": 1,
        "uk_text1": "a",
        "uk_bool1": 0,
        "text2": "'; delete test",
    }
    cur = insert(con, "test", data)
    assert cur is not None
    rowid = cur.lastrowid
    result = con.execute("SELECT * FROM test ORDER BY rowid").fetchall()
    assert len(result) == 1
    assert result[0] == data | {"test_id": rowid}


def test_update(db_connection: sqlite3.Connection) -> None:
    test_id = 1
    insert_data = [
        {
            "test_id": test_id,
            "uk_num1": 1,
            "uk_text1": "a",
            "uk_bool1": 0,
            "text2": "xxxx",
        },
        {
            "uk_num1": 2,
            "uk_text1": "a",
            "uk_bool1": 0,
            "text2": "'; delete test",
        },
    ]
    update_data = {
        "uk_num1": 99,
        "uk_text1": "abc",
        "uk_bool1": 1,
        "text2": "'; delete from test;",
    }
    for d in insert_data:
        insert(db_connection, "test", d)
    update(db_connection, "test", update_data, {"test_id": 1})
    result = db_connection.execute("SELECT * FROM test ORDER BY rowid").fetchall()
    assert len(result) == 2
    assert result[0] == update_data | {"test_id": 1}
    assert result[1] == insert_data[1] | {"test_id": 2}


def test_insert_empty_data(db_connection: sqlite3.Connection) -> None:
    assert insert(db_connection, "test", {}) is None


def test_update_empty_data(db_connection: sqlite3.Connection) -> None:
    assert update(db_connection, "test", {}, {"test_id": 1}) is None


def test_insert_injection_value(db_connection: sqlite3.Connection) -> None:
    data = {
        "uk_num1": 1,
        "uk_text1": "a",
        "uk_bool1": 0,
        "text2": "'); DROP TABLE test; --",
    }
    insert(db_connection, "test", data)
    insert(
        db_connection,
        "test",
        {
            "uk_num1": 2,
            "uk_text1": "b",
            "uk_bool1": 0,
            "text2": "safe",
        },
    )
    result = db_connection.execute("SELECT * FROM test ORDER BY rowid").fetchall()
    assert len(result) == 2
    assert result[0]["text2"] == "'); DROP TABLE test; --"


def test_update_injection_value(db_connection: sqlite3.Connection) -> None:
    insert_data = {
        "test_id": 1,
        "uk_num1": 1,
        "uk_text1": "a",
        "uk_bool1": 0,
        "text2": "before",
    }
    insert(db_connection, "test", insert_data)
    update(
        db_connection,
        "test",
        {"text2": "'); DROP TABLE test; --"},
        {"test_id": 1},
    )
    result = db_connection.execute("SELECT * FROM test").fetchall()
    assert len(result) == 1
    assert result[0]["text2"] == "'); DROP TABLE test; --"


def test_delete_injection_value(db_connection: sqlite3.Connection) -> None:
    insert(
        db_connection,
        "test",
        {
            "test_id": 1,
            "uk_num1": 1,
            "uk_text1": "a",
            "uk_bool1": 0,
            "text2": "x",
        },
    )
    insert(
        db_connection,
        "test",
        {
            "test_id": 2,
            "uk_num1": 2,
            "uk_text1": "b",
            "uk_bool1": 0,
            "text2": "y",
        },
    )
    delete(db_connection, "test", {"test_id": "' OR '1'='1"})
    result = db_connection.execute("SELECT * FROM test ORDER BY rowid").fetchall()
    assert len(result) == 2


def test_getClass(db_connection_with_tables: sqlite3.Connection) -> None:
    con = db_connection_with_tables
    cur = insert(
        con,
        "class_master",
        {
            "class_cd": "testclass",
            "class_name": "テスト区分",
        },
    )
    assert cur is not None
    class_id = cur.lastrowid
    data = [
        {
            "class_id": class_id,
            "class_dtl_cd": "testclass_1",
            "class_dtl_name": "テストクラス1",
            "view_order": 10,
        },
        {
            "class_id": class_id,
            "class_dtl_cd": "testclass_2",
            "class_dtl_name": "テストクラス2",
            "view_order": 9,
        },
        {
            "class_id": class_id,
            "class_dtl_cd": "xxx",
            "class_dtl_name": "yyy",
            "view_order": 8,
        },
    ]
    for d in data:
        insert(con, "class_dtl_master", d)

    result = getClass(con, "testclass")
    assert result == [
        {"value": "xxx", "name": "yyy"},
        {"value": "testclass_2", "name": "テストクラス2"},
        {"value": "testclass_1", "name": "テストクラス1"},
    ]


def test_getClass_injection_value(
    db_connection_with_tables: sqlite3.Connection,
) -> None:
    con = db_connection_with_tables
    cur = insert(
        con,
        "class_master",
        {
            "class_cd": "testclass",
            "class_name": "テスト区分",
        },
    )
    assert cur is not None
    insert(
        con,
        "class_dtl_master",
        {
            "class_id": cur.lastrowid,
            "class_dtl_cd": "testclass_1",
            "class_dtl_name": "テストクラス1",
            "view_order": 10,
        },
    )
    assert getClass(con, "' OR '1'='1") == []
    assert getClass(con, "testclass') --") == []


@pytest.mark.parametrize(
    "payload",
    [
        "' OR '1'='1",
        "' UNION SELECT class_dtl_cd, class_dtl_name FROM class_dtl_master--",
        "' AND 1=1--",
        "testclass' --",
    ],
)
def test_getClass_injection_values_safe(
    db_connection_with_tables: sqlite3.Connection, payload: str
) -> None:
    con = db_connection_with_tables
    insert(con, "class_master", {"class_cd": "testclass", "class_name": "テスト区分"})
    assert getClass(con, payload) == []


def test_select_table_name_injection_escaped(insert_cars: sqlite3.Connection) -> None:
    con = insert_cars
    with pytest.raises(sqlite3.OperationalError):
        select(con, "car WHERE make='Tesla'", ["make"], [])
    rows = con.execute("SELECT * FROM car ORDER BY car_id").fetchall()
    assert len(rows) == 2


def test_select_order_by_injection_escaped(insert_cars: sqlite3.Connection) -> None:
    con = insert_cars
    with pytest.raises(sqlite3.OperationalError):
        select(con, "car", ["price DESC"], [])
    with pytest.raises(sqlite3.OperationalError):
        select(con, "car", ["price; DROP TABLE car;--"], [])


def test_insert_column_name_injection_escaped(
    db_connection: sqlite3.Connection,
) -> None:
    con = db_connection
    data = {
        "uk_text1`: 1, text2 = 'x' --": 1,
        "uk_num1": 1,
    }
    with pytest.raises(sqlite3.OperationalError):
        insert(con, "test", data)
    result = con.execute("SELECT * FROM test").fetchall()
    assert result == []
    insert(con, "test", {"uk_num1": 1, "uk_text1": "a", "uk_bool1": 0, "text2": "ok"})
    assert len(con.execute("SELECT * FROM test").fetchall()) == 1


def test_update_set_column_injection_escaped(insert_cars: sqlite3.Connection) -> None:
    con = insert_cars
    with pytest.raises(sqlite3.OperationalError):
        update(con, "car", {"make = 'Hacked' WHERE 1=1 --": "x"}, {"car_id": 1})
    rows = con.execute("SELECT make FROM car ORDER BY car_id").fetchall()
    assert [r["make"] for r in rows] == ["Tesla", "Ford"]


def test_update_where_column_injection_escaped(insert_cars: sqlite3.Connection) -> None:
    con = insert_cars
    with pytest.raises(sqlite3.OperationalError):
        update(con, "car", {"price": 1}, {"car_id` = 1 --": 1})
    rows = con.execute("SELECT price FROM car ORDER BY car_id").fetchall()
    assert [r["price"] for r in rows] == [50000, 30000]
