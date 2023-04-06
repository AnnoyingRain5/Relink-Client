import websockets
import asyncio
import aioconsole
import communication
import json

CURSOR_UP = '\033[F'
ERASE_LINE = '\033[K'

YELLOW = '\033[33m'
RED = '\033[31m'
BLUE = '\033[94m'
NORMAL = '\033[0m'

username = ""


async def PacketReciever(websocket):
    while True:
        packet = communication.packet(await websocket.recv())
        match type(packet):
            case communication.message:
                await messageHandler(websocket, packet)  # type: ignore
            case communication.command:
                await commandHandler(websocket, packet)  # type: ignore
            case communication.system:
                await SystemMessageHandler(websocket, packet)  # type: ignore
            case _:
                print(type(packet))


async def messageHandler(websocket, message: communication.message):
    if message.username == username:
        print(f"{CURSOR_UP}{BLUE}{message.username}{NORMAL}: {message.text}")
    else:
        print(f"{RED}{message.username}{NORMAL}: {message.text}")


async def SystemMessageHandler(websocket, message: communication.system):
    finalmessage = ""
    if message.response:
        finalmessage += CURSOR_UP
    finalmessage += f"{YELLOW}{message.text}{NORMAL}"
    print(finalmessage)


async def commandHandler(websocket, command: communication.command):
    pass


async def inputmanager(websocket):
    while True:
        # TODO: work out what type of message it is
        message = await aioconsole.ainput()
        if not message.startswith("/"):  # message is a message
            print(CURSOR_UP + ERASE_LINE)
            encoded = communication.message()
            encoded.text = message
            encoded.username = username
            await websocket.send(encoded.json)
        else:  # message is a command
            print(CURSOR_UP + ERASE_LINE)
            encoded = communication.command()
            arglist = message.split()
            arglist[0] = arglist[0].removeprefix("/")
            encoded.name = arglist[0]
            # do not include the name argument
            encoded.args = arglist[1:len(arglist)]
            await websocket.send(encoded.json)


async def main():
    # connect and log in or sign up to the server
    server_address = input(
        "Please enter the IP address or domain name (excluding port) of the server you wish to connect to: ")
    print("Please wait while we attempt to connect to the server...")

    async with websockets.connect(  # type: ignore
            f"ws://{server_address}:8765") as websocket:
        global username
        action = input(
            "Log in or sign up? Type l for login and s for sign up: ").lower()
        if action == "s":  # sign up
            while True:
                username = await aioconsole.ainput("What username will you go by? ")
                password = await aioconsole.ainput(
                    "Make an unforgettable password: ")
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
        elif action == "l":  # log in
            while True:
                username = await aioconsole.ainput("What is your username? ")
                password = await aioconsole.ainput("What is your password? ")
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

        # we are now fully logged into the server, start the main script
        PktRcvTask = asyncio.create_task(PacketReciever(websocket))
        InputManTask = asyncio.create_task(inputmanager(websocket))
        # both of these loop forever, so technically we do not need to wait for both of them
        await PktRcvTask
        await InputManTask

asyncio.run(main())
