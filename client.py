import websockets
import asyncio
import aioconsole
import communication
import json

CURSOR_UP = '\033[F'
ERASE_LINE = '\033[K'

username = ""
global server_address


async def PacketReciever(websocket):
    while True:
        packet = communication.packet(await websocket.recv())
        match type(packet):
            case communication.message:
                await messageHandler(websocket, packet)
            case communication.command:
                await commandHandler(websocket, packet)
            case _:
                print(type(packet))


async def messageHandler(websocket, message: communication.message):
    finalmessage = f"{message.username}: {message.text}"
    if message.username == username:
        print(CURSOR_UP + finalmessage)
    else:
        print(finalmessage)


async def commandHandler(websocket, command: communication.command):
    pass


async def inputmanager(websocket):
    while True:
        # TODO: work out what type of message it is
        message = await aioconsole.ainput()
        print(CURSOR_UP + ERASE_LINE)
        encoded = communication.message()
        encoded.text = message
        encoded.username = username
        await websocket.send(encoded.json)


async def main():
    server_address = input(
        "Please enter the IP address or domain name (excluding port) of the server you wish to connect to: ")
    print("Please wait while we attempt to connect to the server...")
    async with websockets.connect(f"ws://{server_address}:8765") as websocket:
        global username
        action = input(
            "Log in or sign up? Type l for login and s for sign up").lower()
        if action == "s":  # sign up
            while True:
                username = input("What username will you go by? ")
                password = input("Make an unforgettable password: ")
                packet = communication.signupRequest()
                packet.username = username
                packet.password = password
                print("Please wait...")
                await websocket.send(packet.json)
                response = communication.result()
                response.json = await websocket.recv()
                if response.result == True:
                    print("Login successful!")
                    break
                else:
                    print("Denied! Please try again...")
                    print(f"The server said: {response.reason}")
                break
        elif action == "l":  # log in
            while True:
                username = input("What is your username? ")
                password = input("What is your password? ")
                packet = communication.loginRequest()
                packet.username = username
                packet.password = password
                print("Please wait...")
                await websocket.send(packet.json)
                response = communication.result()
                response.json = await websocket.recv()
                if response.result == True:
                    print("Login successful!")
                    break
                else:
                    print("Denied! Please try again...")
                    print(f"The server said: {response.reason}")
                break

        PktRcvTask = asyncio.create_task(PacketReciever(websocket))
        InputManTask = asyncio.create_task(inputmanager(websocket))
        await PktRcvTask
        await InputManTask

asyncio.run(main())
