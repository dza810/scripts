import contextlib
import sqlite3
from abc import ABC, abstractmethod
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

"""
async なしの場合 fastapi が別スレッドで動かしてしまう。
=> handler メソッドで async にできるようにここにもつける
"""
async def get_connection(dbname="data.db"):
    with contextlib.closing(sqlite3.connect(dbname)) as con, con:
        con.row_factory = dict_factory
        con.autocommit = False
        yield con

def get_connection_sync(dbname="data.db"):
    with contextlib.closing(sqlite3.connect(dbname)) as con, con:
        con.row_factory = dict_factory
        con.autocommit = False
        yield con

DbConnection = Annotated[sqlite3.Connection, Depends(get_connection)]

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

class Register(BaseModel):
    updateList: list[dict]
    deleteList: list[Any]
    insertList: list[dict]


class InvalidKeyException(Exception):
    def __init__(self, name: str):
        self.name = name


@app.exception_handler(InvalidKeyException)
async def invalid_key_exception(request: Request, exc: InvalidKeyException):
    return JSONResponse(
        status_code=418, content={"message": f"invalid key: {exc.name}"}
    )


@app.get("/")
async def root():
    return FileResponse("index.html")


def handleSqlValue(v) -> str:
    if v is None:
        return "NULL"
    if v is True:
        return "1"
    if v is False:
        return "0"
    return str(v)


def makeEqCondition(k, v) -> tuple[str, Any]:
    if v is None:
        return f"`{k}` is NULL", None
    else:
        return f"`{k}` = ?", handleSqlValue(v)

def insert(con, table_name, data: dict) -> sqlite3.Cursor | None:
    if len(data) == 0:
        return None
    sql = f"""
        INSERT INTO {table_name} (
          {",\n  ".join(f"`{k}`" for k in data)}
        ) VALUES (
          {",\n  ".join(f":{k}" for k in data)}
        )
        """
    logger.debug(sql)
    return con.execute(sql, {k: handleSqlValue(v) for k, v in data.items()})


def update(con, table_name, data: dict, where: dict) -> sqlite3.Cursor | None:
    if len(data) == 0:
        return None
    conditions = [makeEqCondition(k, v) for k, v in where.items()]
    sql = f"""
    UPDATE {table_name}
    SET
      {", ".join(f"{k} = ?" for k in data)}
    WHERE
      {" AND ".join(v[0] for v in conditions)}
    """
    params = list(data.values()) + [v[1] for v in conditions if v[1] is not None]
    logger.debug('sql=', sql, 'params=', params)
    return con.execute(sql, params)

def delete(con, table_name, where: dict) -> sqlite3.Cursor | None:
    conditions = [makeEqCondition(k, v) for k, v in where.items()]
    sql = f"""
    DELETE FROM {table_name}
    WHERE
      {" AND ".join(v[0] for v in conditions)}
    """
    params = [v[1] for v in conditions if v[1] is not None]
    logger.debug('sql=', sql, 'params=', params)
    return con.execute(sql, params)


def getClass(con, class_cd) -> list[dict[str, Any]]:
    sql = """
      SELECT
        class_dtl_cd as value,
        class_dtl_name as name
      FROM class_dtl_master
      JOIN class_master on class_master.class_master_id = class_dtl_master.class_id
      WHERE class_master.class_cd = :class_cd
      ORDER BY class_dtl_master.view_order
      """
    params = {"class_cd": class_cd}
    logger.debug('sql=', sql, 'params=', params)
    return con.execute(sql, params).fetchall()


class ScreenCls(ABC):
    def __init__(self, con, screen_cd):
        self.con = con
        self.screen_cd = screen_cd

    @abstractmethod
    def update(self, update: Register): ...

    @abstractmethod
    def search(self, params: dict[str, Any]) -> list[dict[str, Any]]: ...

    def make_condition_query(self, option, key, value):
        column_cd = option.get("column_cd")
        queries = []
        match option["condition_cd"]:
            case "equal":
                queries.append(makeEqCondition(column_cd, value))
            case "lesser_than_or_equal":
                queries.append((f"`{column_cd}` <= ?", handleSqlValue(value)))
            case "greater_than_or_equal":
                queries.append((f"? <= `{column_cd}`", handleSqlValue(value)))
            case "between":
                value_from = value.get("from")
                if value_from:
                    queries.append((f"`{column_cd}` >= ?", handleSqlValue(value_from)))
                value_to = value.get("to")
                if value_to:
                    queries.append((f"`{column_cd}` <= ?", handleSqlValue(value_to)))
            case "contains":
                for word in value.split(" "):
                    queries.append((f"`{column_cd}` like ('%' || ? || '%')", handleSqlValue(word)))
            case _:
                logger.warning('skip', option)
        return queries

    def make_condition(self, params) -> list[tuple[str, Any]]:
        options = {v["search_form_cd"]: v for v in self.getSearchForm()}
        queries = []
        for key, value in params.items():
            option = options.get(key)
            if option is None:
                raise InvalidKeyException(key)
            queries.extend(self.make_condition_query(option, key, value))
        return queries

    def _search(self, params: dict[str, Any], table_name, order_by):
        logger.debug(table_name, order_by, params)
        conditions = self.make_condition(params)
        sql = f"""
            SELECT
                rowid as id,
                *
            FROM {table_name}
            {"" if len(conditions) == 0 else f"WHERE {' AND '.join(v[0] for v in conditions)}"}
            ORDER BY {", ".join(order_by)}
        """
        logger.debug(sql)
        paramsSql = [v[1] for v in conditions]
        logger.debug(paramsSql)
        return self.con.execute(sql, paramsSql).fetchall()

    def run_insert(self, table_name, data):
        logger.debug("insert", table_name, data)
        self._check_column_key(data.keys())
        return insert(self.con, table_name, data)

    def run_update(self, table_name, data, where):
        logger.debug("update", table_name, data)
        self._check_column_key(data.keys())
        return update(self.con, table_name, data, where)

    def run_delete(self, table_name, where):
        logger.debug("delete", table_name)
        return delete(self.con, table_name, where)

    def _update(self, table_name, update):
        for ins_row in update.insertList:
            self.run_insert(table_name, ins_row)

        for del_id in update.deleteList:
            self.run_delete(table_name, {f"{table_name}_id": del_id})

        for upd_row in update.updateList:
            self.run_update(
                table_name,
                {k: v for k, v in upd_row.items() if k != "id"},
                {f"{table_name}_id": upd_row["id"]},
            )

    def _check_column_key(self, keys):
        columns = {
            v
            for v in {col.get("column_name") for col in self.getColumnOptions()}
            if v is not None
        }
        for key in keys:
            if key not in columns:
                raise InvalidKeyException(key)
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

    def getSearchForm(self):
        return self.con.execute(
            """
            SELECT
                search_form.search_form_cd,
                search_form.search_form_name,
                column.column_cd,
                column.column_name,
                column.type,
                column.dropdown_class_cd,
                search_form.view_order,
                search_form_condition.condition_cd
            FROM search_form
            JOIN search_form_condition ON search_form.condition_id = search_form_condition.search_form_condition_id
            JOIN column ON search_form.column_id = column.column_id
            JOIN screen ON screen.screen_id = search_form.screen_id
            WHERE screen_cd = :screen_cd
            ORDER BY search_form.view_order, search_form.search_form_cd, search_form.search_form_name
            """,
            {"screen_cd": self.screen_cd},
        ).fetchall()


class ScreenMaster(ScreenCls):
    def search(self, params: dict[str, Any]):
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


class SearchFormMaster(ScreenCls):
    def search(self, params):
        return self._search(params, "search_form", ["search_form_id"])

    def update(self, update):
        self._update("search_form", update)


class RowStyleMaster(ScreenCls):
    def search(self, params):
        return self._search(params, "row_style", ["1", "2", "3"])

    def update(self, update):
        self._update("row_style", update)


class InvalidScreenException(Exception):
    pass


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
    if screen_cd == "search_form_master":
        return SearchFormMaster(con, screen_cd)
    raise InvalidScreenException(screenCd)


Screen = Annotated[ScreenCls, Depends(get_screen)]


@app.post("/search")
async def search(screen: Screen, params: dict[str, Any]) -> list[dict[str, Any]]:
    return screen.search(params["params"])


@app.post("/register")
async def register(dbConnection: DbConnection, screen: Screen, update: Register):
    screen.update(update)


@app.get("/getClass")
async def _getClass(code: str, dbConnection: DbConnection):
    return getClass(dbConnection, code)


@app.get("/getColumns")
async def getColumns(screen: Screen, dbConnection: DbConnection):
    columnOptions = screen.getColumnOptions()
    for col in columnOptions:
        if col["type"] == "dropdown":
            logger.debug("getColumns")
            col["classes"] = getClass(dbConnection, col["dropdown_class_cd"])

    rowStyles = screen.getRowStyle()
    return {"columnOptions": columnOptions, "rowStyles": rowStyles}


@app.get("/getSearchForms")
async def getSearchForms(screen: Screen):
    searchForms = screen.getSearchForm()
    return searchForms

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
