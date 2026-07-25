import sqlite3
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


async def get_connection():
    with sqlite3.connect("data.db") as con:
        con.row_factory = dict_factory
        con.autocommit = False
        yield con


DbConnection = Annotated[sqlite3.Connection, Depends(get_connection)]

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("index.html")


def handleSqlValue(v):
    if v is None:
        return "NULL"
    if v is True:
        return 1
    if v is False:
        return 0
    return v


def makeEqCondition(k, v):
    if v is None:
        return f"`{k}` is ?", "NULL"
    else:
        return f"`{k}` = ?", handleSqlValue(v)


def insert(con, table_name, data: dict):
    sql = f"""
    INSERT INTO {table_name} (
      {",\n  ".join(f"`{k}`" for k in data)}
    ) VALUES (
      {",\n  ".join(f":{k}" for k in data)}
    )
    """
    print(sql)
    return con.execute(sql, {k: handleSqlValue(v) for k, v in data.items()})


def update(con, table_name, data: dict, where: dict):
    conditions = [makeEqCondition(k, v) for k, v in where.items()]
    sql = f"""
    UPDATE {table_name}
    SET
      {", ".join(f"{k} = ?" for k in data)}
    WHERE
      {" AND ".join(v[0] for v in conditions)}
    """
    print(sql)
    params = list(data.values()) + [v[1] for v in conditions]
    print(params)
    return con.execute(sql, params)


def _getClass(con, class_cd):
    return con.execute(
        """
      SELECT
        class_dtl_cd as value,
        class_dtl_name as name
      FROM class_dtl_master
      JOIN class_master on class_master.class_master_id = class_dtl_master.class_id
      WHERE class_master.class_cd = :class_cd
      ORDER BY class_dtl_master.view_order
      """,
        {"class_cd": class_cd},
    ).fetchall()


class ScreenCls:
    def __init__(self, con, screen_cd):
        self.con = con
        self.screen_cd = screen_cd

    def _search(self, params, table_name, order_by):
        conditions = [makeEqCondition(k, v) for k, v in params.items()]
        sql = f"""
            SELECT
                rowid as id,
                *
            FROM {table_name}
            {"" if len(params) == 0 else f"WHERE {' AND '.join(v[0] for v in conditions)}"}
            ORDER BY {", ".join(order_by)}
        """
        print(sql)
        params = [v[1] for v in conditions]
        print(params)
        return self.con.execute(sql, params).fetchall()

    def run_insert(self, table_name, data):
        print("insert", table_name, data)
        self._check_key(data.keys())
        return insert(self.con, table_name, data)

    def run_update(self, table_name, data, where):
        print("update", table_name, data)
        self._check_key(data.keys())
        return update(self.con, table_name, data, where)

    def _update(self, table_name, update):
        for ins_row in update.insertList:
            self.run_insert(table_name, ins_row)
        for del_id in update.deleteList:
            self.run_insert(table_name, {f"{table_name}_id": del_id})
        for upd_row in update.updateList:
            self.run_update(
                table_name,
                {k: v for k, v in upd_row.items() if k != "id"},
                {f"{table_name}_id": upd_row["id"]},
            )

    def _check_key(self, keys):
        columns = {
            v
            for v in {col.get("column_name") for col in self.getColumnOptions()}
            if v is not None
        }
        for key in keys:
            if key not in columns:
                raise Exception("invalid key")
        return columns

    def getRowStyle(self):
        return self.con.execute(
            """
            SELECT
                row_style.row_style_code_condition as code,
                row_style.row_style_code_style as style
            FROM row_style
            JOIN screen ON screen.screen_id = row_style.screen_id
            WHERE screen_cd = :screen_cd
            ORDER BY row_style_cd
            """,
            {"screen_cd": self.screen_cd},
        ).fetchall()

    def getColumnOptions(self):
        return self.con.execute(
            """
            SELECT *
            FROM column
            JOIN screen ON screen.screen_id = column.screen_id
            WHERE screen_cd = :screen_cd
            ORDER BY view_order, column_cd, column_name
            """,
            {"screen_cd": self.screen_cd},
        ).fetchall()


class ScreenMaster(ScreenCls):
    def search(self, params):
        return self._search(params, "screen", ["screen_cd"])

    def update(self, update):
        self._update("screen", update)


class ColumnMaster(ScreenCls):
    def search(self, params):
        return self._search(params, "column", ["view_order", "column_cd"])

    def update(self, update):
        self._update("column", update)


class CarList(ScreenCls):
    def search(self, params):
        return self._search(params, "car", ["make", "model"])

    def update(self, update):
        self._update("car", update)


class ClassMaster(ScreenCls):
    def search(self, params):
        return self._search(params, "class_master", ["screen_id", "class_cd"])

    def update(self, update):
        self._update("class_master", update)


class ClassDtlMaster(ScreenCls):
    def search(self, params):
        return self._search(params, "class_dtl_master", ["class_id", "class_dtl_cd"])

    def update(self, update):
        self._update("class_dtl_master", update)


class RowStyleMaster(ScreenCls):
    def search(self, params):
        sql = f"""
            SELECT
                row_style.rowid as id,
                row_style.*
            FROM row_style
            {"" if len(params) == 0 else f"WHERE {" AND ".join(makeEqCondition(k, v) for k, v in params.items())}"}
            ORDER BY 1, 2, 3
        """
        print(sql)
        return self.con.execute(sql).fetchall()

    def update(self, update):
        self._update("row_style", update)


def get_screen(screenCd: str, con: DbConnection) -> ScreenCls:
    screen_cd = screenCd
    if screen_cd == "column_master":
        return ColumnMaster(con, screen_cd)
    if screen_cd == "screen_master":
        return ScreenMaster(con, screen_cd)
    if screen_cd == "car_list":
        return CarList(con, screen_cd)
    if screen_cd == "class_master":
        return ClassMaster(con, screen_cd)
    if screen_cd == "class_dtl_master":
        return ClassDtlMaster(con, screen_cd)
    if screen_cd == "row_style_master":
        return RowStyleMaster(con, screen_cd)
    raise Exception("invalid screen code")


Screen = Annotated[ScreenCls, Depends(get_screen)]


@app.post("/search")
async def search(
    screen: Screen, params: dict[str, Any], dbConnection: DbConnection
) -> list[dict[str, Any]]:
    return screen.search(params["params"])


class Register(BaseModel):
    updateList: list[dict]
    deleteList: list[Any]
    insertList: list[dict]


@app.post("/register")
async def register(screen: Screen, update: Register):
    screen.update(update)


@app.get("/getClass")
async def getClass(code: str, dbConnection: DbConnection):
    return _getClass(dbConnection, code)


@app.get("/getColumns")
async def getColumns(screen: Screen, dbConnection: DbConnection):
    columnOptions = screen.getColumnOptions()
    for col in columnOptions:
        if col["type"] == "dropdown":
            col["classes"] = _getClass(dbConnection, col["dropdown_class_cd"])

    rowStyles = screen.getRowStyle()
    return {"columnOptions": columnOptions, "rowStyles": rowStyles}
