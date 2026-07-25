from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from typing import Any
from pydantic import BaseModel, Json
from asyncio import sleep
from fastapi.staticfiles import StaticFiles


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("index.html")


def _getClass(code: str):
    if code == "make":
        out = []
        for v in ["Tesla", "Ford", "Toyota"]:
            out.append({"value": "cd" + v, "name": v})
        return out

    for i in range(3):
        out.append({"value": str(i), "name": f"{code}-{i}"})

    return out


@app.get("/getClass")
async def getClass(code: str, request: Request):
    return _getClass(code)


@app.get("/getColumns")
async def getColumns():
    columnOptions = [
        {
            "type": "dropdown",
            "field": "make",
            "code": "make",
            "classes": _getClass("make"),
        },
        {
            "type": "autoCalc",
            "viewName": "自動計算",
            "code": """getField("make")+"123" """,
        },
        {"type": "text", "field": "model", "required": True},
        {
            "type": "number",
            "field": "price",
            "cellStyleCode": """getField('price') > 30000""",
            "cellStyleCodeStyle": """ { "background-color": "red" } """,
        },
        {
            "type": "checkbox",
            "field": "electric",
        },
    ]
    rowStyles = [
        {
            "code": """ getField("electric") """,
            "style": """ { "background-color": "yellow" } """,
        },
        {
            "code": """ getField("model") == "Model Y" """,
            "style": """ { "background-color": "gray" } """,
        },
    ]
    return {"rowStyles": rowStyles, "columnOptions": columnOptions}


data = [
    {"id": 1, "make": "cdTesla", "model": "Model Y", "price": 64950, "electric": False},
    {"id": 2, "make": "cdFord", "model": "F-Series", "price": 33850, "electric": False},
    {
        "id": 3,
        "make": "cdToyota",
        "model": "Corolla",
        "price": 29600,
        "electric": False,
    },
    {"id": 4, "make": "cdTesla", "model": "Model Y2", "price": 64950, "electric": True},
    {"id": 5, "make": "cdFord", "model": "F-Series2", "price": 33850, "electric": True},
    {
        "id": 6,
        "make": "cdToyota",
        "model": "Corolla2",
        "price": 29600,
        "electric": True,
    },
]


@app.post("/search")
async def search(params: dict[str, Any]):
    result = [d for d in data]
    for k, v in params.items():
        if v == "true":
            v = True
        elif v == "false":
            v = False
        if v != "":
            result = [d for d in result if d.get(k) is None or d.get(k) == v]
    return result


class Register(BaseModel):
    beforeList: list[dict[str, Any]]
    afterList: list[dict[str, Any]]


@app.post("/register")
async def register(update: Register):
    global data
    currentDataById = {d.get("id"): d for d in data}
    print(currentDataById)
    beforeDataById = {d.get("id"): d for d in update.beforeList}
    print(beforeDataById)
    for ad in update.afterList:
        id_ = ad.get("id")
        bd = beforeDataById.get(id_, {})
        for k, av in ad.items():
            if av != bd.get(k):
                currentDataById[id_][k] = av
