import websockets
import asyncio
import aioconsole
import json

CURSOR_UP = '\033[F'
ERASE_LINE = '\033[K'

username = input("what is your name? ")

server_address = input("Please enter the IP address (excluding port) of the server you wish to connect to")

async def hello(websocket):
    while True:
        message = await websocket.recv()
        decoded = json.loads(message)
        finalmessage = f"{decoded['username']}: {decoded['message']}"
        if decoded["username"] == username:
            print(CURSOR_UP + finalmessage)
        else:
            print(finalmessage)

            
async def inputmanager(websocket):
    while True:
        message = await aioconsole.ainput()
        print(CURSOR_UP + ERASE_LINE)
        encoded = json.dumps({"username": username, "message": message})
        await websocket.send(encoded)

async def main():
    async with websockets.connect(f"ws://{server_address}:8765") as websocket:
        task1 = asyncio.create_task(hello(websocket))
        task2 = asyncio.create_task(inputmanager(websocket))
        await task1
        await task2

asyncio.run(main())