from fastapi import FastAPI
from fastapi.responses import FileResponse
from typing import Any
from pydantic import BaseModel

app = FastAPI()

storage = { }

@app.get("/")
async def root():
    return FileResponse("index.html")

@app.get("/index.js")
async def root():
    return FileResponse("index.js")

class PostPubKey(BaseModel):
    name: str
    exportedPublicKey: dict


@app.post("/postPubKey", response_model=None)
async def postPubKey(
    postPubKey: PostPubKey
):
    global storage
    print(postPubKey)
    storage[postPubKey.name] = postPubKey.exportedPublicKey
    return { 'result': "OK" }

@app.get("/getPubKey")
async def getPubKey(
        name: str
):
    global storage
    return storage[name]

class SendMessageTo(BaseModel):
    name: str
    oppName: str
    encrypted: Any

@app.post("/sendMessageTo")
async def sendMessageTo(
    sendMessageTo: SendMessageTo
):
    storage[f"{sendMessageTo.name}->{sendMessageTo.oppName}"] = sendMessageTo
    return { 'result': "OK" }

@app.get("/getMessage")
async def getMessage(
    name: str,
    oppName: str,
):
    return storage[f"{oppName}->{name}"] 
