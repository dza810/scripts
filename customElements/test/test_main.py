from fastapi.testclient import TestClient
from proj.main import *
import pytest
from proj import setupSqlite


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

