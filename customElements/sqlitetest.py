import pprint
import sqlite3


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def connect():
    con = sqlite3.connect("data.db")
    con.row_factory = dict_factory
    con.autocommit = False
    return con


class Column:
    code: str
    type_: str
    in_uniq: bool
    not_null: bool


def column(code, type_, *, in_uniq=False, not_null=False, default=None):
    col = Column()
    col.code = code
    if type_ == "number":
        col.type_ = "integer"
    if type_ == "checkbox":
        col.type_ = "boolean"
    else:
        col.type_ = type_
    col.in_uniq = in_uniq
    col.not_null = not_null
    col.default = default
    return col


class Table:
    name: str
    cols: list[Column]


def table(name, cols):
    t = Table()
    t.name = name
    t.cols = cols
    return t


screen_table = table(
    "screen",
    [
        column("screen_cd", "text", in_uniq=True, not_null=True),
        column("screen_name", "text", not_null=True),
    ],
)

column_table = table(
    "column",
    [
        column("screen_id", "text", in_uniq=True, not_null=True),
        column("column_cd", "text", in_uniq=True, not_null=True),
        column("column_name", "text", not_null=True),
        column("type", "text", not_null=True),
        column("view_order", "number", not_null=True),
        column("required", "boolean", not_null=True, default="FALSE"),
        column("cell_style_code_condition", "text"),
        column("cell_style_code_style", "text"),
        # dropdown
        column("dropdown_class_cd", "text"),
        # auto_calc
        column("auto_calc_code", "text"),
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

car_table = table(
    "car",
    [
        column("make", "text", in_uniq=True, not_null=True),
        column("model", "text", in_uniq=True, not_null=True),
        column("price", "number"),
        column("electric", "checkbox"),
    ],
)

class_table = table(
    "class_master",
    [
        column("class_cd", "text", in_uniq=True, not_null=True),
        column("class_name", "text", not_null=True),
    ],
)

class_dtl_table = table(
    "class_dtl_master",
    [
        column("class_id", "class", in_uniq=True, not_null=True),
        column("class_dtl_cd", "text", in_uniq=True, not_null=True),
        column("class_dtl_name", "text", not_null=True),
        column("is_default", "checkbox", not_null=True, default="FALSE"),
        column("view_order", "number"),
    ],
)


def create_table_sql(table):
    table_name = table.name
    cols = table.cols
    cols_sql = ",\n  ".join(
        [
            " ".join(
                v
                for v in [
                    f"`{col.code}`",
                    col.type_,
                    "NOT NULL" if col.not_null else None,
                    f"DEFAULT `{col.default}`" if col.default is not None else None,
                ]
                if v != "" and v is not None
            )
            for col in cols
        ]
    )
    uniq_sql = ", ".join([f"`{col.code}`" for col in cols if col.in_uniq])
    sql = f"""
      CREATE TABLE {table_name} (
        `{table_name}_id` integer primary key autoincrement,
        {cols_sql}
        {"" if len(uniq_sql) == 0 else f", unique ({uniq_sql})"}
      )"""
    print(sql)
    return sql


def insert(con, table_name, data: dict):
    sql = f"""
    INSERT INTO {table_name} (
      {",\n  ".join(k for k in data)}
    ) VALUES (
      {",\n  ".join(f":{k}" for k in data)}
    )
    """
    print(sql)
    return con.execute(sql, data)


def make_table(con, table, screen_cd, screen_name):
    con.execute(create_table_sql(table))

    screen_id = insert(
        con, "screen", {"screen_cd": screen_cd, "screen_name": screen_name}
    ).lastrowid

    for i, col in enumerate(table.cols):
        insert(
            con,
            "column",
            {
                "screen_id": screen_id,
                "view_order": i,
                "column_cd": col.code,
                "column_name": col.code,
                "type": col.type_,
            },
        )


# def setup():
#     with connect() as con:
#         con.execute(create_table_sql(screen_table))
#         con.execute(create_table_sql(column_table))
# 
#         # insert
#         screen_master_id = insert(
#             con,
#             screen_table.name,
#             {"screen_cd": "screen_master", "screen_name": "画面管理"},
#         ).lastrowid
# 
#         column_master_id = insert(
#             con,
#             screen_table.name,
#             {"screen_cd": "column_master", "screen_name": "列管理"},
#         ).lastrowid
# 
#         ## 画面管理用の設定
#         for i, col in enumerate(screen_table.cols):
#             insert(
#                 con,
#                 column_table.name,
#                 {
#                     "screen_id": screen_master_id,
#                     "view_order": i,
#                     "column_cd": col.code,
#                     "column_name": col.code,
#                     "type": col.type_,
#                 },
#             )
# 
#         for i, col in enumerate(column_table.cols):
#             insert(
#                 con,
#                 column_table,
#                 {
#                     "screen_id": column_master_id,
#                     "view_order": i,
#                     "column_cd": col.code,
#                     "column_name": col.code,
#                     "type": col.type_,
#                 },
#             )
# 
# 
with connect() as con:
    sql = """
    SELECT
      *
    FROM screen
    ORDER BY 1,2,3
    """
    print(sql)
    print("---")
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(con.execute(sql).fetchall())


# def setup_class_tables():
#     with connect() as con:
#         con.execute("DROP TABLE IF EXISTS class_master")
#         con.execute("DROP TABLE IF EXISTS class_dtl_master")
#         con.execute(
#             "DELETE FROM column WHERE screen_id = (SELECT screen_id FROM screen WHERE screen_cd = 'class_master')"
#         )
#         con.execute(
#             "DELETE FROM column WHERE screen_id = (SELECT screen_id FROM screen WHERE screen_cd = 'class_dtl_master')"
#         )
#         con.execute("DELETE FROM screen WHERE screen_cd = 'class_master'")
#         con.execute("DELETE FROM screen WHERE screen_cd = 'class_dtl_master'")
# 
#     with connect() as con:
#         make_table(con, class_table, "class_master", "区分値管理")
#         make_table(con, class_dtl_table, "class_dtl_master", "区分値明細管理")
# 
#         make_class_id = insert(
#             con, class_table.name, {"class_cd": "make", "class_name": "make"}
#         ).lastrowid
#         for v in ["Tesla", "Ford", "Toyota"]:
#             insert(
#                 con,
#                 class_dtl_table.name,
#                 {"class_id": make_class_id, "class_dtl_cd": v, "class_dtl_name": v},
#             )
# 
# 
# def setup_row_style():
#     with connect() as con:
#         table = row_style_table
#         screen_cd = "row_style_master"
#         con.execute(f"DROP TABLE IF EXISTS {table.name}")
#         con.execute(
#             "DELETE FROM column WHERE screen_id = (SELECT screen_id FROM screen WHERE screen_cd = ?)",
#             [screen_cd]
#         )
#         con.execute("DELETE FROM screen WHERE screen_cd = ?", [screen_cd])
# 
#         make_table(con, table, screen_cd, "行スタイルマスタ")
#         screen_id = con.execute("SELECT screen_id FROM screen WHERE screen_cd = ?", [screen_cd]).fetchone()["screen_id"]
#         insert(
#             con,
#             table.name,
#             {"screen_id": screen_id, "row_style_cd": "1", "row_style_name": "テスト"},
#         )


# setup_row_style()
