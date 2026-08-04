import sqlite3
from typing import Any, Literal

sqliteStrictAllowedTypes = Literal["INT", "INTEGER", "REAL", "TEXT", "BLOB", "ANY"]
SQLITE_STRICT_ALLOWD_TYPES = ["INT", "INTEGER", "REAL", "TEXT", "BLOB", "ANY"]


def dict_factory(cursor: sqlite3.Cursor, row: tuple[Any, ...]) -> dict[str, Any]:
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def connect(dbname: str):
    con = sqlite3.connect(dbname)
    con.row_factory = dict_factory
    con.autocommit = False
    return con


class Column:
    code: str
    type_: str
    data_type: str
    in_uniq: bool
    not_null: bool
    default: Any
    editable: bool
    dropdown_class_cd: str | None
    max_length: int | None


def column(
    code: str,
    type_: str,
    *,
    data_type: str | None = None,
    in_uniq: bool = False,
    not_null: bool = False,
    default: Any = None,
    dropdown_class_cd: str | None = None,
    max_length: int | None = None,
    editable: bool = True,
) -> Column:
    col = Column()
    col.code = code

    if data_type is None:
        if type_ == "dropdown":
            col.data_type = "text"
        elif type_ == "number" or type_ == "checkbox":
            col.data_type = "integer"
        else:
            col.data_type = type_
    else:
        col.data_type = data_type

    col.type_ = type_

    col.in_uniq = in_uniq
    col.not_null = not_null
    col.default = default
    col.dropdown_class_cd = dropdown_class_cd
    col.max_length = max_length
    col.editable = editable
    return col


class Table:
    name: str
    cols: list[Column]


def table(name: str, cols: list[Column]) -> Table:
    t = Table()
    t.name = name
    t.cols = cols
    return t


screen_table = table(
    "screen",
    [
        column("screen_cd", "text", in_uniq=True, not_null=True, editable=False),
        column("screen_name", "text", not_null=True),
    ],
)

column_table = table(
    "column",
    [
        column("screen_id", "text", in_uniq=True, not_null=True, editable=False),
        column("column_cd", "text", in_uniq=True, not_null=True, editable=False),
        column("column_name", "text", not_null=True),
        column("type", "text", not_null=True),
        column("view_order", "number", not_null=True),
        column("required", "checkbox", not_null=True, default=0),
        column("editable", "checkbox", not_null=True, default=1),
        column("cell_style_code_condition", "text"),
        column("cell_style_code_style", "text"),
        column("max_length", "number"),
        # dropdown
        column("dropdown_class_cd", "text"),
        # auto_calc
        column("auto_calc_code", "text"),
    ],
)

search_form_condition_table = table(
    "search_form_condition",
    [
        column("condition_cd", "text", in_uniq=True, not_null=True, editable=False),
        column("condition_name", "text", not_null=True),
    ],
)

search_form_table = table(
    "search_form",
    [
        column("screen_id", "text", in_uniq=True, not_null=True),
        column("search_form_cd", "text", in_uniq=True, not_null=True),
        column("search_form_name", "text", in_uniq=True, not_null=True),
        column("column_id", "number", not_null=True),
        column("condition_id", "number", not_null=True),
        column("view_order", "number", not_null=True),
        column("required", "checkbox", not_null=True, default=0),
    ],
)


row_style_table = table(
    "row_style",
    [
        column("screen_id", "text", in_uniq=True, not_null=True),
        column("row_style_cd", "text", in_uniq=True, not_null=True),
        column("row_style_name", "text", not_null=True),
        column("row_style_code_condition", "text"),
        column("row_style_code_style", "text"),
    ],
)

class_table = table(
    "class_master",
    [
        column("class_cd", "text", in_uniq=True, not_null=True, editable=False),
        column("class_name", "text", not_null=True),
    ],
)

class_dtl_table = table(
    "class_dtl_master",
    [
        column("class_id", "number", in_uniq=True, not_null=True, editable=False),
        column("class_dtl_cd", "text", in_uniq=True, not_null=True, editable=False),
        column("class_dtl_name", "text", not_null=True),
        column("is_default", "checkbox", not_null=True, default=0),
        column("view_order", "number"),
    ],
)

car_table = table(
    "car",
    [
        column(
            "make",
            "dropdown",
            data_type="text",
            in_uniq=True,
            not_null=True,
            dropdown_class_cd="make",
        ),
        column("model", "text", in_uniq=True),
        column("price", "number"),
        column("electric", "checkbox"),
    ],
)


def create_table_sql(table: Table) -> str:
    table_name = table.name
    cols = table.cols
    for col in table.cols:
        assert col.data_type.upper() in SQLITE_STRICT_ALLOWD_TYPES, (
            f"型が不正です。{table.name}.{col.code},{col.type_},{col.data_type}"
        )

    cols_sql = [
        " ".join(
            v
            for v in [
                f"`{col.code}`",
                col.data_type,
                "NOT NULL" if col.not_null else None,
                f"DEFAULT {"'" + col.default + "'" if isinstance(col.default, str) else col.default}"
                if col.default is not None
                else None,
            ]
            if v != "" and v is not None
        )
        for col in cols
    ]
    foreign_keys = [
        f"foreign key (`{col.code}`) references `{col.code[: -len('_id')]}({col.code})`"
        for col in cols
        if col.code.endswith("_id")
    ]
    uniq_sql = ", ".join([f"`{col.code}`" for col in cols if col.in_uniq])
    sql = f"""
      CREATE TABLE {table_name} ({
        ",".join(
            [f"`{table_name}_id` integer primary key autoincrement"]
            + cols_sql
            + [f"unique ({uniq_sql})"]
            + foreign_keys
        )
    }) STRICT"""
    print(sql)
    return sql


def _make_insert_statement(
    con: sqlite3.Connection, table_name: str, data: dict[str, Any]
) -> str:
    return f"""
    INSERT INTO {table_name} (
      {",\n  ".join(k for k in data)}
    ) VALUES (
      {",\n  ".join(f":{k}" for k in data)}
    )
    """


def insert(
    con: sqlite3.Connection, table_name: str, data: dict[str, Any]
) -> sqlite3.Cursor:
    sql = _make_insert_statement(con, table_name, data)
    print(sql)
    return con.execute(sql, data)


def setup_table_util(
    con: sqlite3.Connection,
    table: Table,
    screen_cd: str,
    screen_name: str,
) -> None:
    screen_id = insert(
        con,
        screen_table.name,
        {"screen_cd": screen_cd, "screen_name": screen_name},
    ).lastrowid

    for i, col in enumerate(table.cols):
        column_id = insert(
            con,
            column_table.name,
            {
                "screen_id": screen_id,
                "view_order": i,
                "column_cd": col.code,
                "column_name": col.code,
                "type": col.type_,
                "dropdown_class_cd": col.dropdown_class_cd,
                "max_length": col.max_length,
                "required": col.not_null,
                "editable": col.editable,
            },
        ).lastrowid

        insert(
            con,
            search_form_table.name,
            {
                "screen_id": screen_id,
                "search_form_cd": col.code,
                "search_form_name": col.code,
                "column_id": column_id,
                "condition_id": 1,  # equal
                "view_order": i,
            },
        )


def make_table(
    con: sqlite3.Connection, table: Table, screen_cd: str, screen_name: str
) -> None:
    con.execute(create_table_sql(table))
    setup_table_util(con, table, screen_cd, screen_name)


def setup_screen_column(con: sqlite3.Connection) -> None:
    con.execute(create_table_sql(screen_table))
    con.execute(create_table_sql(column_table))
    con.execute(create_table_sql(search_form_table))

    setup_table_util(con, screen_table, "screen_master", "画面管理")
    setup_table_util(con, column_table, "column_master", "列管理")
    setup_table_util(con, search_form_table, "search_form_master", "検索条件管理")


def setup_class_tables(con: sqlite3.Connection) -> None:
    make_table(con, class_table, "class_master", "区分値管理")
    make_table(con, class_dtl_table, "class_dtl_master", "区分値明細管理")

    make_class_id = insert(
        con, class_table.name, {"class_cd": "make", "class_name": "make"}
    ).lastrowid
    for v in ["Tesla", "Ford", "Toyota"]:
        insert(
            con,
            class_dtl_table.name,
            {"class_id": make_class_id, "class_dtl_cd": f"cd{v}", "class_dtl_name": v},
        )


def get_screen_id(con: sqlite3.Connection, screen_cd: str) -> Any:
    screen_id = con.execute(
        "SELECT screen_id FROM screen WHERE screen_cd = ?", [screen_cd]
    ).fetchone()["screen_id"]
    return screen_id


def setup_row_style(con: sqlite3.Connection) -> None:
    table = row_style_table
    screen_cd = "row_style_master"

    make_table(con, table, screen_cd, "行スタイルマスタ")
    screen_id = get_screen_id(con, screen_cd)
    insert(
        con,
        table.name,
        {"screen_id": screen_id, "row_style_cd": "1", "row_style_name": "テスト"},
    )


def setup_search_form_condition(con: sqlite3.Connection) -> None:
    table = search_form_condition_table
    screen_cd = "search_form_condition"

    make_table(con, table, screen_cd, "検索フォーム条件マスタ")
    insert(con, table.name, {"condition_cd": "equal", "condition_name": "等しい"})
    insert(
        con,
        table.name,
        {"condition_cd": "lesser_than_or_equal", "condition_name": "以下"},
    )
    insert(
        con,
        table.name,
        {"condition_cd": "greater_than_or_equal", "condition_name": "以下"},
    )
    insert(con, table.name, {"condition_cd": "between", "condition_name": "間"})


def setup(con: sqlite3.Connection):
    setup_screen_column(con)
    setup_search_form_condition(con)
    setup_row_style(con)
    make_table(con, car_table, "car_list", "カーリスト")
    setup_class_tables(con)


if __name__ == "__main__":
    import sys

    dbname = sys.argv[1]
    assert dbname, "dbname を指定してください"
    with connect(dbname) as con:
        setup(con)
