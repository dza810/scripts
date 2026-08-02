import pytest

from proj.db import insert, makeConditionQuery
from proj.main import (
    CarList,
    ClassDtlMaster,
    ClassMaster,
    ColumnMaster,
    InvalidKeyException,
    InvalidScreenException,
    Register,
    RowStyleMaster,
    ScreenMaster,
    SearchFormMaster,
    get_screen,
)


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
def test_make_condition_query(condition_cd, value, expected):
    assert makeConditionQuery("price", condition_cd, value) == expected


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


# -------------------------------------------------------------
# SQLインジェクション対策のテスト（Screen層）
# -------------------------------------------------------------
SEARCH_INJECTION_VALUES = [
    # boolean-based
    "' OR '1'='1",
    "' OR '1'='1' --",
    "' OR 1=1--",
    "' OR 1=1 #",
    "' AND '1'='1",
    "' AND 1=1--",
    "' AND 1=2--",
    "' OR 1=1/*",
    # union-based
    "' UNION SELECT 1,2,3,4--",
    "' UNION SELECT make, model, price, electric FROM car--",
    "' UNION SELECT NULL, NULL, NULL, NULL--",
    # error-based
    "' AND extractvalue(1, concat(0x7e, version()))--",
    "' AND 1=CONVERT(int, @@version)--",
    # time-based
    "' AND (SELECT IF(1=1, SLEEP(5), 0))--",
    "'; WAITFOR DELAY '0:0:5'--",
    # stacked queries
    "'; DROP TABLE car;--",
    "'); DROP TABLE car; --",
    "' OR 1=1; DROP TABLE car;--",
    # getClass 経由の注入
    "' UNION SELECT class_dtl_cd, class_dtl_name FROM class_dtl_master--",
]


@pytest.mark.parametrize("payload", SEARCH_INJECTION_VALUES)
def test_search_injection_values_safe(insert_cars, payload):
    con = insert_cars
    screen = get_screen("car_list", con)
    result = screen.search({"model": payload})
    assert result == []
    rows = con.execute("SELECT * FROM car ORDER BY car_id").fetchall()
    assert len(rows) == 2


SEARCH_INJECTION_KEYS = [
    "`make`",
    "`model`",
    "make` = `model` --",
    "make; DROP TABLE car;--",
    "model' OR '1'='1",
    "price) OR (1=1",
    "' OR 1=1--",
]


@pytest.mark.parametrize("key", SEARCH_INJECTION_KEYS)
def test_search_injection_key_rejected(db_connection_with_tables, key):
    con = db_connection_with_tables
    screen = get_screen("car_list", con)
    with pytest.raises(InvalidKeyException):
        screen.make_condition({key: 1})
    with pytest.raises(InvalidKeyException):
        screen.search({key: 1})


@pytest.mark.parametrize("key", SEARCH_INJECTION_KEYS)
def test_register_insert_injection_column_key_rejected(db_connection_with_tables, key):
    con = db_connection_with_tables
    screen = get_screen("car_list", con)
    with pytest.raises(InvalidKeyException):
        screen.run_insert("car", {key: 1})


@pytest.mark.parametrize("key", SEARCH_INJECTION_KEYS)
def test_register_update_injection_column_key_rejected(db_connection_with_tables, key):
    con = db_connection_with_tables
    screen = get_screen("car_list", con)
    with pytest.raises(InvalidKeyException):
        screen.run_update("car", {key: 1}, {"car_id": 1})


@pytest.mark.parametrize("screen_cd", [
    "car_list'; DROP TABLE car;--",
    "car_list' OR '1'='1 --",
    "car_list UNION SELECT 1,2,3--",
])
def test_get_screen_injection_rejected(db_connection_with_tables, screen_cd):
    con = db_connection_with_tables
    with pytest.raises(InvalidScreenException):
        get_screen(screen_cd, con)


def test_search_union_injection_no_data_leak(insert_cars):
    con = insert_cars
    screen = get_screen("car_list", con)
    assert screen.search({"model": "' OR '1'='1"}) == []
    assert screen.search({"model": "x' UNION SELECT make, model, price, electric FROM car--"}) == []


def test_select_injection_value(db_connection_with_tables):
    con = db_connection_with_tables
    insert(con, "car", {"make": "Tesla", "model": "Model 3", "price": 100, "electric": 1})
    insert(con, "car", {"make": "Ford", "model": "Focus", "price": 200, "electric": 0})
    screen = get_screen("car_list", con)
    result = screen.search({"model": "' OR '1'='1"})
    assert result == []
    result = screen.search({"model": "Focus"})
    assert len(result) == 1
    assert result[0]["make"] == "Ford"


def test_delete_injection_where_value_safe(insert_cars):
    con = insert_cars
    screen = get_screen("car_list", con)
    screen.run_delete("car", {"car_id": "1 OR 1=1; DROP TABLE car;--"})
    rows = con.execute("SELECT * FROM car ORDER BY car_id").fetchall()
    assert len(rows) == 2


def test_register_update_injection_id_safe(insert_cars):
    con = insert_cars
    screen = get_screen("car_list", con)
    screen.update(Register(
        insertList=[],
        deleteList=[],
        updateList=[{"id": "1 OR 1=1--", "price": 999}],
    ))
    prices = [r["price"] for r in con.execute("SELECT price FROM car ORDER BY car_id").fetchall()]
    assert prices == [50000, 30000]


def test_register_delete_injection_id_safe(insert_cars):
    con = insert_cars
    screen = get_screen("car_list", con)
    screen.update(Register(
        insertList=[],
        deleteList=["1 OR 1=1; DROP TABLE car;--"],
        updateList=[],
    ))
    rows = con.execute("SELECT * FROM car ORDER BY car_id").fetchall()
    assert len(rows) == 2


def test_second_order_injection_safe(db_connection_with_tables):
    con = db_connection_with_tables
    screen = get_screen("car_list", con)
    payload = "'; DROP TABLE car;--"
    screen.run_insert("car", {"make": "Tesla", "model": payload, "price": 1, "electric": 0})
    found = screen.search({"model": payload})
    assert len(found) == 1
    assert found[0]["model"] == payload
    assert len(con.execute("SELECT * FROM car").fetchall()) == 1


def test_sql_truncation_injection_stored_as_is(db_connection_with_tables):
    con = db_connection_with_tables
    screen = get_screen("car_list", con)
    payload = "admin   '--"
    screen.run_insert("car", {"make": "Tesla", "model": payload, "price": 1, "electric": 0})
    assert screen.search({"model": "admin"}) == []
    found = screen.search({"model": payload})
    assert len(found) == 1
