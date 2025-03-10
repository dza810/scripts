import signal
import asyncio
import websockets
import logging

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)

async def send_task(websocket):
    while True:
        message = await asyncio.to_thread(input)
        if message.lower() == "exit":
            print("接続を終了します。")
            break
        await websocket.send(message)
        print(f"送信: {message}", flush=True)

async def recv_task(websocket):
    while True:
        response = await websocket.recv()
        print(f"受信: {response}", flush=True)

async def check_task(*tasks):
    while True:
        for t in tasks:
            print(t)
        await asyncio.sleep(1000)

async def simple_client():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        async def shutdown(loop):
            await websocket.close()
            tasks = [t for t in asyncio.all_tasks() if t is not
             asyncio.current_task()]
            logger.info(",".join(map(repr,tasks)))

            [task.cancel() for task in tasks]
            logger.info("waiting for cancelling tasks")
            await asyncio.gather(*tasks)
            logger.info("all tasks cancelled")
            loop.stop()
            
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, lambda : asyncio.create_task(shutdown(loop)))

        async with asyncio.TaskGroup() as tg:
            t1 = tg.create_task(send_task(websocket), name="send")
            t2 = tg.create_task(recv_task(websocket), name="recv")
            tg.create_task(check_task(t1, t2))
        await websocket.wait_closed()

asyncio.run(simple_client())

