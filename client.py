import websockets
import asyncio
import aioconsole
import communication
import os
import math

CURSOR_HOME = '\033[H'
CURSOR_UP = '\033[F'
ERASE_LINE = '\033[K'
ERASE_SCREEN = '\033[2J'

BLUE_BACKGROUND = '\033[48;5;57m'
YELLOW = '\033[33m'
RED = '\033[31m'
BLUE = '\033[94m'
NORMAL = '\033[0m'

username = ""
messages = []
DMs: dict[str, list[communication.message]] = {}
CurrentChannel = "Unknown (not supplied by server?)"
serverAddress = ""


class notificationlist():
    def __init__(self):
        self.dict: dict[str, int] = {}

    def __len__(self) -> int:
        total = 0
        for item in self.dict:
            total += self.dict[item]
        return total

    def add(self, channel):
        global CurrentChannel
        if channel == CurrentChannel:
            return
        try:
            self.dict[channel] += 1
        except KeyError:  # if this is the first message for this
            self.dict[channel] = 1

    def markRead(self, channel):
        self.dict[channel] = 0

    def MarkAllRead(self):
        self.dict = {}


notifications = notificationlist()


def renderText():
    lines = os.get_terminal_size().lines
    columns = os.get_terminal_size().columns
    topstr = f"({len(notifications)}) - #{CurrentChannel}@{serverAddress}"
    middle = math.floor(columns / 2)
    print(f"{ERASE_SCREEN}{CURSOR_HOME}{BLUE_BACKGROUND}", end="")
    for column in range(middle - math.floor(len(topstr) / 2)):
        print(" ", end="")
    print(topstr, end="")
    for column in range(middle - math.ceil(len(topstr) / 2)):
        print(" ", end="")
    print(NORMAL)
    for message in messages:
        if "\n" in message:
            lines -= (message.count("\n"))
            continue
        plain = message.replace(YELLOW, "").replace(
            RED, "").replace(BLUE, "").replace(NORMAL, "")
        lines -= math.ceil(len(plain) / columns) - 1
    while len(messages) > lines - 2:
        message = messages.pop(0)
        lines += (message.count("\n"))
        plain = message.replace(YELLOW, "").replace(
            RED, "").replace(BLUE, "").replace(NORMAL, "")
        lines += math.ceil(len(plain) / columns) - 1
    for line in range(lines - 2):
        try:
            print(messages[line])
        except:
            print("")


async def PacketReciever(websocket):
    while True:
        # Get a packet from the server and convert the JSON to it's type
        rawPacket = await websocket.recv()
        packet = communication.packet(rawPacket)
        # Run the correct handler for the packet type
        match type(packet):
            case communication.message:
                await messageHandler(websocket, packet)  # type: ignore
            case communication.command:
                await commandHandler(websocket, packet)  # type: ignore
            case communication.system:
                await SystemMessageHandler(websocket, packet)  # type: ignore
            case communication.channelChange:
                await ChannelChangeHandler(websocket, packet)  # type: ignore
            case communication.notification:
                await notificationHandler(websocket, packet)  # type: ignore
            case _:  # if the client does not understand what type of packet it is
                warning = f"{YELLOW} Warning: Recieved an unknown message from the server! "
                warning += f"Perhaps you need to update your client? The raw JSON recieved is as follows: "
                warning += f"{NORMAL}{rawPacket}"
                messages.append(warning)
                renderText()


async def messageHandler(websocket, message: communication.message):
    if not message.isDM:
        if message.username == username:
            messages.append(
                f"{BLUE}{message.username}{NORMAL}: {message.text}")
        else:
            messages.append(f"{RED}{message.username}{NORMAL}: {message.text}")
        renderText()
    else:  # the message is a DM
        # if we are in the correct channel or it is our own message
        if f"@{message.username}" == CurrentChannel or message.username == username:

            print(message.username)
            if message.username == username:
                messages.append(
                    f"{BLUE}{message.username}{NORMAL}: {message.text}")
            else:
                messages.append(
                    f"{RED}{message.username}{NORMAL}: {message.text}")
            renderText()
        else:
            # send notification
            notification = communication.notification()
            notification.type = "DM"
            notification.location = f"@{message.username}"
            await notificationHandler(None, notification)
            # add the DM to the DMs dictionary
            try:
                DMs[f"@{message.username}"].append(message)
            except KeyError:
                DMs[f"@{message.username}"] = [message]


async def SystemMessageHandler(websocket, message: communication.system):
    messages.append(f"{YELLOW}{message.text}{NORMAL}")
    renderText()


async def commandHandler(websocket, command: communication.command):
    pass


async def ChannelChangeHandler(websocket, message: communication.channelChange):
    global CurrentChannel
    global messages
    global notifications
    CurrentChannel = message.channel
    messages = []
    notifications.markRead(message.channel)
    if CurrentChannel.startswith("@"):
        try:
            for dm in DMs[CurrentChannel]:
                if dm.username == username:
                    messages.append(
                        f"{BLUE}{dm.username}{NORMAL}: {dm.text}")
                else:
                    messages.append(
                        f"{RED}{dm.username}{NORMAL}: {dm.text}")
        except KeyError:
            pass
    renderText()


async def notificationHandler(websocket, notification: communication.notification):
    # TODO add proper notification support
    if notification.type == "mention":
        text = f"{YELLOW}You got a new mention in #{notification.location}!{NORMAL}\a"
    elif notification.type == "DM":
        text = f"{YELLOW}New DM from {notification.location}{NORMAL}\a"
    else:
        text = "New unknown notification.\a"
    global notifications
    notifications.add(notification.location)
    messages.append(text)
    renderText()


async def inputmanager(websocket):
    while True:
        message = await aioconsole.ainput()
        if not message.startswith("/"):  # message is a message
            print(CURSOR_UP + ERASE_LINE)
            encoded = communication.message()
            encoded.text = message
            encoded.username = username
            encoded.isDM = CurrentChannel.startswith("@")
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
    global serverAddress
    serverAddress = input(
        "Please enter the IP address or domain name (excluding port) of the server you wish to connect to: ")
    print("Please wait while we attempt to connect to the server...")
    try:
        async with websockets.connect(  # type: ignore
                f"ws://{serverAddress}:8765") as websocket:
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
            renderText()  # render the screen for the first time
            # both of these loop forever, so technically we do not need to wait for both of them
            await PktRcvTask
            await InputManTask
    except websockets.exceptions.ConnectionClosedOK:  # type: ignore
        print(f"{YELLOW}The connection has been closed by the server.{NORMAL}")

asyncio.run(main())
