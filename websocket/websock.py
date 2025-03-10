import asyncio
from datetime import datetime
import websockets
import logging
logging.basicConfig(level=logging.DEBUG)

async def handler(websocket):
    print(datetime.now(), "Client connected")
    try:
        while True:
            message = await websocket.recv()
            print(datetime.now(),f"Received: {message}")
            await websocket.send(f"Echo: {message}")
    except websockets.exceptions.ConnectionClosedError:
        print(datetime.now(), "Client disconnected")

async def main():
    print(datetime.now(), "server start")
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())

