import contextlib
import sqlite3
from typing import Any, Literal

from loguru import logger

ConditionCode = Literal[
    "equal",
    "lesser_than_or_equal",
    "greater_than_or_equal",
    "between",
    "contains",
]


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


def handleSqlValue(v) -> str:
    if v is None:
        return "NULL"
    if v is True:
        return "1"
    if v is False:
        return "0"
    return str(v)


def quote_ident(name: str) -> str:
    return f"`{name.replace('`', '``')}`"


def makeEqCondition(k, v) -> tuple[str, Any]:
    if v is None:
        return f"{quote_ident(k)} is NULL", None
    else:
        return f"{quote_ident(k)} = ?", handleSqlValue(v)

def insert(con, table_name, data: dict) -> sqlite3.Cursor | None:
    if len(data) == 0:
        return None
    sql = f"""
        INSERT INTO {quote_ident(table_name)} (
          {",\n  ".join(quote_ident(k) for k in data)}
        ) VALUES (
          {",\n  ".join("?" for _ in data)}
        )
        """
    logger.debug(sql)
    return con.execute(sql, [handleSqlValue(v) for v in data.values()])


def update(con, table_name, data: dict, where: dict) -> sqlite3.Cursor | None:
    if len(data) == 0:
        return None
    conditions = [makeEqCondition(k, v) for k, v in where.items()]
    sql = f"""
    UPDATE {quote_ident(table_name)}
    SET
      {", ".join(f"{quote_ident(k)} = ?" for k in data)}
    WHERE
      {" AND ".join(v[0] for v in conditions)}
    """
    params = list(data.values()) + [v[1] for v in conditions if v[1] is not None]
    logger.debug('sql=', sql, 'params=', params)
    return con.execute(sql, params)

def delete(con, table_name, where: dict) -> sqlite3.Cursor | None:
    conditions = [makeEqCondition(k, v) for k, v in where.items()]
    sql = f"""
    DELETE FROM {quote_ident(table_name)}
    WHERE
      {" AND ".join(v[0] for v in conditions)}
    """
    params = [v[1] for v in conditions if v[1] is not None]
    logger.debug('sql=', sql, 'params=', params)
    return con.execute(sql, params)


def select(
    con, table_name: str, order_by: list[str], conditions: list[tuple[str, Any]]
) -> list[dict[str, Any]]:
    sql = f"""
        SELECT
            rowid as id,
            *
        FROM {quote_ident(table_name)}
        {"" if len(conditions) == 0 else f"WHERE {' AND '.join(v[0] for v in conditions)}"}
        ORDER BY {", ".join(quote_ident(c) for c in order_by)}
    """
    paramsSql = [v[1] for v in conditions]
    logger.debug('sql=', sql, 'params=', paramsSql)
    return con.execute(sql, paramsSql).fetchall()


def makeConditionQuery(column, condition: ConditionCode, value) -> list[tuple[str, Any]]:
    queries = []
    match condition:
        case "equal":
            queries.append(makeEqCondition(column, value))
        case "lesser_than_or_equal":
            queries.append((f"{quote_ident(column)} <= ?", handleSqlValue(value)))
        case "greater_than_or_equal":
            queries.append((f"? <= {quote_ident(column)}", handleSqlValue(value)))
        case "between":
            value_from = value.get("from")
            if value_from:
                queries.append((f"{quote_ident(column)} >= ?", handleSqlValue(value_from)))
            value_to = value.get("to")
            if value_to:
                queries.append((f"{quote_ident(column)} <= ?", handleSqlValue(value_to)))
        case "contains":
            for word in value.split(" "):
                queries.append((f"{quote_ident(column)} like ('%' || ? || '%')", handleSqlValue(word)))
        case _:
            logger.warning('skip', condition)
    return queries


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


def getRowStyle(con, screen_cd) -> list[dict[str, Any]]:
    return con.execute(
        """
        SELECT
            row_style.row_style_code_condition as code,
            row_style.row_style_code_style as style
        FROM row_style
        JOIN screen ON screen.screen_id = row_style.screen_id
        WHERE screen_cd = :screen_cd
        ORDER BY row_style_cd
        """,
        {"screen_cd": screen_cd},
    ).fetchall()


def getColumnOptions(con, screen_cd) -> list[dict[str, Any]]:
    return con.execute(
        """
        SELECT *
        FROM column
        JOIN screen ON screen.screen_id = column.screen_id
        WHERE screen_cd = :screen_cd
        ORDER BY view_order, column_cd, column_name
        """,
        {"screen_cd": screen_cd},
    ).fetchall()


def getSearchForm(con, screen_cd) -> list[dict[str, Any]]:
    return con.execute(
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
        {"screen_cd": screen_cd},
    ).fetchall()
