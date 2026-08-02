import hmac
import secrets
import sqlite3
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Annotated, Any

from fastapi import Cookie, Depends, FastAPI, Header, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel

from proj.db import (
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


class CsrfException(Exception): ...


@app.get("/getCsrfToken")
async def get_csrf_token(response: Response):
    token = secrets.token_urlsafe(32)
    response.delete_cookie(key="csrftoken")
    response.set_cookie(key="csrftoken", value=token, samesite="lax")
    return {"type": "ok"}


@app.exception_handler(CsrfException)
async def csrf_exception_handler(request: Request, exc: CsrfException) -> JSONResponse:
    return JSONResponse(status_code=403, content={"message": "csrf token mismatch"})


async def check_csrf_token(
    token_header: Annotated[str | None, Header(alias="csrftoken")] = None,
    token_cookie: Annotated[str | None, Cookie(alias="csrftoken")] = None,
):
    if token_header is None or token_cookie is None:
        raise CsrfException()

    if not hmac.compare_digest(token_header.encode(), token_cookie.encode()):
        raise CsrfException()


CheckCsrfToken = Annotated[None, Depends(check_csrf_token)]


class Register(BaseModel):
    updateList: list[dict[str, Any]]
    deleteList: list[Any]
    insertList: list[dict[str, Any]]


class InvalidKeyException(Exception):
    def __init__(self, name: str):
        self.name = name


@app.exception_handler(InvalidKeyException)
async def invalid_key_exception(
    request: Request, exc: InvalidKeyException
) -> JSONResponse:
    return JSONResponse(
        status_code=418, content={"message": f"invalid key: {exc.name}"}
    )


@app.get("/")
async def root() -> FileResponse:
    return FileResponse("index.html")


class ScreenCls(ABC):
    def __init__(self, con: sqlite3.Connection, screen_cd: str):
        self.con = con
        self.screen_cd = screen_cd

    @abstractmethod
    def update(self, update: Register) -> None: ...

    @abstractmethod
    def search(self, params: dict[str, Any]) -> list[dict[str, Any]]: ...

    def make_condition(self, params: dict[str, Any]) -> list[tuple[str, Any]]:
        options = {v["search_form_cd"]: v for v in self.getSearchForm()}
        queries = []
        new_params = {}
        for key, value in params.items():
            if "::" in key:
                keys = key.split("::")
                new_params[keys[0]] = new_params.get(keys[0], {})
                valueTmp = new_params[keys[0]]
                for k in keys[1:-1]:
                    valueTmp[k] = valueTmp.get(k, {})
                    valueTmp = valueTmp[k]
                valueTmp[keys[-1]] = value
            else:
                new_params[key] = value

        for key, value in new_params.items():
            option = options.get(key)
            if option is None:
                raise InvalidKeyException(key)
            if option["type"] == "checkbox":
                if value == "false":
                    new_params[key] = False
                elif value == "true":
                    new_params[key] = True
                else:
                    raise ValueError(f"invalid value: {key}")

        for key, value in new_params.items():
            option = options.get(key)
            if option is None:
                raise InvalidKeyException(key)
            queries.extend(
                makeConditionQuery(option["column_cd"], option["condition_cd"], value)
            )
        return queries

    def _search(
        self,
        params: dict[str, Any],
        table_name: str,
        order_by: list[str],
    ) -> list[dict[str, Any]]:
        conditions = self.make_condition(params)
        return select(self.con, table_name, order_by, conditions)

    def run_insert(
        self, table_name: str, data: dict[str, Any]
    ) -> sqlite3.Cursor | None:
        logger.debug("insert", table_name, data)
        self._check_column_key(data.keys())
        return insert(self.con, table_name, data)

    def run_update(
        self,
        table_name: str,
        data: dict[str, Any],
        where: dict[str, Any],
    ) -> sqlite3.Cursor | None:
        logger.debug("update", table_name, data)
        self._check_column_key(data.keys())
        return update(self.con, table_name, data, where)

    def run_delete(
        self, table_name: str, where: dict[str, Any]
    ) -> sqlite3.Cursor | None:
        logger.debug("delete", table_name)
        return delete(self.con, table_name, where)

    def _update(self, table_name: str, update: Register) -> None:
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

    def _check_column_key(self, keys: Iterable[str]) -> set[str]:
        columns = {
            v
            for v in {col.get("column_name") for col in self.getColumnOptions()}
            if v is not None
        }
        for key in keys:
            if key not in columns:
                raise InvalidKeyException(key)
        return columns

    def getRowStyle(self) -> list[dict[str, Any]]:
        return getRowStyle(self.con, self.screen_cd)

    def getColumnOptions(self) -> list[dict[str, Any]]:
        return getColumnOptions(self.con, self.screen_cd)

    def getSearchForm(self) -> list[dict[str, Any]]:
        return getSearchForm(self.con, self.screen_cd)


class ScreenMaster(ScreenCls):
    def search(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        return self._search(params, "screen", ["screen_cd"])

    def update(self, update: Register) -> None:
        self._update("screen", update)


class ColumnMaster(ScreenCls):
    def search(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        return self._search(params, "column", ["view_order", "column_cd"])

    def update(self, update: Register) -> None:
        self._update("column", update)


class CarList(ScreenCls):
    def search(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        return self._search(params, "car", ["make", "model"])

    def update(self, update: Register) -> None:
        self._update("car", update)


class ClassMaster(ScreenCls):
    def search(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        return self._search(params, "class_master", ["screen_id", "class_cd"])

    def update(self, update: Register) -> None:
        self._update("class_master", update)


class ClassDtlMaster(ScreenCls):
    def search(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        return self._search(params, "class_dtl_master", ["class_id", "class_dtl_cd"])

    def update(self, update: Register) -> None:
        self._update("class_dtl_master", update)


class SearchFormMaster(ScreenCls):
    def search(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        return self._search(params, "search_form", ["search_form_id"])

    def update(self, update: Register) -> None:
        self._update("search_form", update)


class RowStyleMaster(ScreenCls):
    def search(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        return self._search(params, "row_style", ["1", "2", "3"])

    def update(self, update: Register) -> None:
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
async def search(
    screen: Screen, params: dict[str, Any], _: CheckCsrfToken
) -> list[dict[str, Any]]:
    return screen.search(params["params"])


@app.post("/register")
async def register(
    dbConnection: DbConnection, screen: Screen, update: Register, _: CheckCsrfToken
) -> None:
    screen.update(update)


@app.get("/getClass")
async def _getClass(code: str, dbConnection: DbConnection) -> list[dict[str, Any]]:
    return getClass(dbConnection, code)


@app.get("/getColumns")
async def getColumns(screen: Screen, dbConnection: DbConnection) -> dict[str, Any]:
    columnOptions = screen.getColumnOptions()
    for col in columnOptions:
        if col["type"] == "dropdown":
            logger.debug("getColumns")
            col["classes"] = getClass(dbConnection, col["dropdown_class_cd"])

    rowStyles = screen.getRowStyle()
    return {"columnOptions": columnOptions, "rowStyles": rowStyles}


@app.get("/getSearchForms")
async def getSearchForms(screen: Screen) -> list[dict[str, Any]]:
    searchForms = screen.getSearchForm()
    return searchForms


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
