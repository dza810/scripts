import asyncio
from datetime import datetime
import websockets
import logging
logging.basicConfig(level=logging.DEBUG)

async def recv(q):
    while True:
        message = await websocket.recv()
        print(datetime.now(),f"Received: {message}")
        q.put_nowait(message)

async def send(q):
    while True:
        await websocket.send(f"Echo: {message}")

async def handler(websocket):
    q = asyncio.Queue()
    print(datetime.now(), "Client connected")
    async with TaskGroup() as tg:
        tg.create_task(send(q))
        tg.create_task(recv(q))

async def main():
    print(datetime.now(), "server start")
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())

