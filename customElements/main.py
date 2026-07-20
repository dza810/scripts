from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from typing import Any
from pydantic import BaseModel
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
            out.append({'value': "cd"+v, "name": v})
        return out

    for i in range(3):
        out.append({'value': str(i), 'name': f'{code}-{i}'})

    return out

@app.get("/getClass")
async def getClass(code: str, request: Request):
    return _getClass(code)

@app.get("/getColumns")
async def getColumns():
    return [
      {
        'type': 'dropdown',
        'field': 'make',
        'code': 'make',
        'required': True,
        'classes': _getClass("make")
      },
      {
        'type': 'text',
        'field': 'model',
        'required': True
      },
      {
        'type': 'number',
        'field': 'price',
      },
      {
        'type': 'text',
        'field': 'electric',
      }
    ]

@app.get("/search")
async def search():
    return [
      { 'make': "cdTesla",  'model': "Model Y",  'price': 64950, 'electric': True },
      { 'make': "cdFord",   'model': "F-Series", 'price': 33850, 'electric': False },
      { 'make': "cdToyota", 'model': "Corolla",  'price': 29600, 'electric': False },
      { 'make': "cdToyota", 'model': "Corolla",  'price': 29600, 'electric': False },
      { 'make': "cdToyota", 'model': "Corolla",  'price': 29600, 'electric': False },
      { 'make': "cdToyota", 'model': "Corolla",  'price': 29600, 'electric': False },
      { 'make': "cdToyota", 'model': "Corolla",  'price': 29600, 'electric': False },
    ]
