import sqlite3
from abc import ABC, abstractmethod
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel

from proj.db import (
    ConditionCode,
    delete,
    get_connection,
    getClass,
    getColumnOptions,
    getRowStyle,
    getSearchForm,
    insert,
    makeConditionQuery,
    select,
    update,
)

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


class ScreenCls(ABC):
    def __init__(self, con, screen_cd):
        self.con = con
        self.screen_cd = screen_cd

    @abstractmethod
    def update(self, update: Register): ...

    @abstractmethod
    def search(self, params: dict[str, Any]) -> list[dict[str, Any]]: ...

    def make_condition_query(self, column, condition: ConditionCode, value):
        return makeConditionQuery(column, condition, value)

    def make_condition(self, params) -> list[tuple[str, Any]]:
        options = {v["search_form_cd"]: v for v in self.getSearchForm()}
        queries = []
        for key, value in params.items():
            option = options.get(key)
            if option is None:
                raise InvalidKeyException(key)
            queries.extend(
                self.make_condition_query(option["column_cd"], option["condition_cd"], value)
            )
        return queries

    def _search(self, params: dict[str, Any], table_name, order_by):
        conditions = self.make_condition(params)
        return select(self.con, table_name, order_by, conditions)

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
        return getRowStyle(self.con, self.screen_cd)

    def getColumnOptions(self):
        return getColumnOptions(self.con, self.screen_cd)

    def getSearchForm(self):
        return getSearchForm(self.con, self.screen_cd)


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
