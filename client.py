import asyncio
import os
import dns.resolver
import math
import websockets.client
import websockets.exceptions
import aioconsole
import Relink_Communication.communication as communication


class NotificationList():
    '''Basic class to handle the notification list'''

    def __init__(self):
        self.dict: dict[str, int] = {}

    def __len__(self) -> int:
        '''Returns the total amount of notifications across all channels'''
        total = 0
        for _, amount in self.dict.items():
            total += amount
        return total

    def add(self, channel: str):
        if channel == CurrentChannel:
            return
        # add 1 to the amount of notifications
        try:
            self.dict[channel] += 1
        except KeyError:  # if this is the first notification for this channel
            self.dict[channel] = 1

    def markRead(self, channel: str):
        self.dict[channel] = 0

    def MarkAllRead(self):
        self.dict = {}


# init constants
CURSOR_HOME = '\033[H'
CURSOR_UP = '\033[F'
ERASE_LINE = '\033[K'
ERASE_SCREEN = '\033[2J'

BLUE_BACKGROUND = '\033[48;5;57m'
YELLOW = '\033[33m'
RED = '\033[31m'
BLUE = '\033[94m'
NORMAL = '\033[0m'

# init variables
username = ""
messages = []
DMs: dict[str, list[communication.Message]] = {}
CurrentChannel = "Unknown (not supplied by server?)"
serverAddress = ""
notifications = NotificationList()
WelcomeNotSent = False
ChannelUserList = []
ServerUserList = []
CommandList = []

def renderText():
    '''Function to handle rendering text to the terminal'''
    # work out the size of the terminal
    lines = os.get_terminal_size().lines
    columns = os.get_terminal_size().columns
    middle = math.floor(columns / 2)
    # if this is a DM channel, don't show the # in front of the channel name
    if CurrentChannel.startswith("@"):
        topstr = f"({len(notifications)}) - {CurrentChannel}"
    else:
        topstr = f"({len(notifications)}) - #{CurrentChannel}"
    # clear the screen and set the background to blue
    print(f"{ERASE_SCREEN}{CURSOR_HOME}{BLUE_BACKGROUND}", end="")
    # print the channel name and amount of notifications text centred to the screen
    for _ in range(middle - math.floor(len(topstr) / 2)):
        print(" ", end="")
    print(topstr, end="")
    for _ in range(middle - math.ceil(len(topstr) / 2)):
        print(" ", end="")
    # now we can reset the colour
    print(NORMAL)
    # for every message in the messages list
    for message in messages:
        if "\n" in message:
            # if the message contains a newline, use that as the authoritative
            # answer for how many lines the message will take up
            lines -= (message.count("\n"))
            continue
        # ignore formatting when calculating amount of lines
        plain = message.replace(YELLOW, "").replace(
            RED, "").replace(BLUE, "").replace(NORMAL, "")
        # calculate the amount of lines the message will take
        lines -= math.ceil(len(plain) / columns) - 1
    while len(messages) > lines - 2:
        # if there are too many message to display
        message = messages.pop(0)  # remove the oldest message
        # add the lines back to the amount of lines available for printing
        lines += (message.count("\n"))
        plain = message.replace(YELLOW, "").replace(
            RED, "").replace(BLUE, "").replace(NORMAL, "")
        lines += math.ceil(len(plain) / columns) - 1
    # for each line, print it's message
    for line in range(lines - 2):
        try:
            print(messages[line])
        except:
            # if there is no message to print, print an empty line instead
            print("")


async def PacketReceiver(websocket):
    '''Main function to handle receiving packets'''
    while True:
        # Get a packet from the server and convert the JSON to it's type
        rawPacket = await websocket.recv()
        packet = communication.packet(rawPacket)
        # Run the correct handler for the packet type
        match type(packet):
            case communication.Message:
                await messageHandler(websocket, packet)  # type: ignore
            case communication.Command:
                await commandHandler(websocket, packet)  # type: ignore
            case communication.System:
                await SystemMessageHandler(websocket, packet)  # type: ignore
            case communication.ChannelChange:
                await ChannelChangeHandler(websocket, packet)  # type: ignore
            case communication.Notification:
                await notificationHandler(websocket, packet)  # type: ignore
            case communication.CommandList:
                await CommandListHandler(websocket, packet) # type: ignore
            case communication.UserList:
                await UserListHandler(websocket, packet) # type: ignore
            case _:
                # if the client does not understand what type of packet it is,
                # warn the user and hint at a possible client update
                warning = f"{YELLOW} Warning: Received an unknown message from the server! "
                warning += "Perhaps you need to update your client? The raw JSON received is as follows: "
                warning += f"{NORMAL}{rawPacket}"
                messages.append(warning)
                renderText()


async def messageHandler(websocket, message: communication.Message):
    '''Handles incoming messages'''
    if not message.isDM:  # if the message is not a DM
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
        else:  # The message is a DM, but we are not in the DM channel
            # send ourselves a notification
            notification = communication.Notification()
            notification.type = "DM"
            notification.location = f"@{message.username}"
            await notificationHandler(None, notification)
            # add the DM to the DMs dictionary
            try:
                DMs[f"@{message.username}"].append(message)
            except KeyError:
                DMs[f"@{message.username}"] = [message]


async def SystemMessageHandler(websocket, message: communication.System):
    '''Handles system messages'''
    messages.append(f"{YELLOW}{message.text}{NORMAL}")
    renderText()

async def CommandListHandler(websocket, message: communication.CommandList):
    '''Handles the list of commands being updated'''
    global CommandList
    CommandList = message.commandList

async def UserListHandler(websocket, message: communication.UserList):
    '''Handles the list of commands being updated'''
    global ServerUserList
    global ChannelUserList
    ServerUserList = message.serverList
    ChannelUserList = message.channelList


async def commandHandler(websocket, command: communication.Command):
    '''Handles the client receiving a command from the server

    Currently stubbed'''
    pass


async def ChannelChangeHandler(websocket, message: communication.ChannelChange):
    '''Handles channel change packets'''
    global CurrentChannel
    global messages
    CurrentChannel = message.channel  # switch the channel variable to the new channel
    messages = []  # wipe the message list
    # mark notifications for the new channel as read
    global WelcomeNotSent
    if WelcomeNotSent:
        messages.append(f"{YELLOW}You have been logged in successfully. Welcome to Relink! Use /help for a list of commands.")
        WelcomeNotSent = False
    notifications.markRead(message.channel)
    # if we are switching to a DM channel
    if CurrentChannel.startswith("@"):
        try:
            # display the DM messages that we have recorded
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


async def notificationHandler(websocket, notification: communication.Notification):
    '''Handles notification packets'''
    # TODO send a system notification if possible
    if notification.type == "mention":
        text = f"{YELLOW}You got a new mention in #{notification.location}!{NORMAL}\a"
    elif notification.type == "DM":
        text = f"{YELLOW}New DM from {notification.location}{NORMAL}\a"
    else:
        text = "New unknown notification.\a"
    # add the notification to the list
    notifications.add(notification.location)
    messages.append(text)
    renderText()  # re-render the screen to include the updated notification count


async def inputmanager(websocket):
    '''Handles input from the user when the enter key is pressed'''
    while True:
        message: str = await aioconsole.ainput()
        if not message.startswith("/"):
            # message is a message (not a command)
            # remove the line where the input is
            print(CURSOR_UP + ERASE_LINE)
            # prepare and send the packet to the server
            encoded = communication.Message()
            encoded.text = message
            encoded.username = username
            encoded.isDM = CurrentChannel.startswith("@")
            await websocket.send(encoded.json)
        else:  # message is a command
            match message.removeprefix("/").lower():
                # match to client commands
                case "inbox":
                    output = ""
                    for channel, amount in notifications.dict.items():
                        if amount != 0:
                            output += f"{channel}: {amount}\n"
                    output = output.removesuffix("\n")
                    messages.append(
                        f"{YELLOW}Notifications:\n{output}{NORMAL}")
                    renderText()
                case "list":
                        message = f"{YELLOW}Users in your channel are: "
                        for user in ChannelUserList:
                            message += f"{user}, "
                        # remove the last comma
                        message = message.removesuffix(", ")
                        message += "\nAll users online on this server are: "
                        for user in ServerUserList:
                            message += f"{user}, "
                        # remove the last comma
                        message = message.removesuffix(", ")
                        messages.append(f"{message}{NORMAL}")
                        renderText()
                case "help":
                    message = f"{YELLOW}Defined commands are as follows:\n"
                    message += "Client commands:\n"
                    for command in ["inbox", "list", "help"]:
                        message += f"/{command}, "
                    # remove the last comma
                    message = message.removesuffix(", ")
                    message += "\nServer commands are as follows:\n"
                    for command in CommandList:
                        message += f"/{command}, "
                    message = message.removesuffix(", ")
                    messages.append(f"{message}{NORMAL}")
                    renderText()
                case "exit":
                    print(f"{YELLOW}Now exiting Relink, Thanks for hanging out!{NORMAL}")
                    await websocket.close()
                case _:
                    # the command must be a server command
                    print(CURSOR_UP + ERASE_LINE)
                    encoded = communication.Command()
                    arglist = message.split()
                    arglist[0] = arglist[0].removeprefix("/")
                    encoded.name = arglist[0]
                    # do not include the name argument
                    encoded.args = arglist[1:len(arglist)]
                    await websocket.send(encoded.json)

async def signup(websocket):
    global username
    while True:
        # get username and password and send them to the server
        print("type cancel to cancel")
        username = await aioconsole.ainput("What username will you go by? ")
        if username == "cancel":
            return False
        password = await aioconsole.ainput(
            "Make an unforgettable password: ")
        if password == "cancel":
            return False
        packet = communication.SignupRequest()
        packet.username = username
        packet.password = password
        print("Please wait...")
        # send the request to the server
        await websocket.send(packet.json)
        response = communication.Result()
        response.json = await websocket.recv()
        if response.result:
            print("Sign up successful!")
            return True
        else:
            # the server denied the request, let the user know and give them a second chance
            print("Denied! Please try again...")
            print(f"The server said: {response.reason}")

async def login(websocket):
    global username
    while True:
        # get username and password from user
        print("type cancel to cancel")
        username = await aioconsole.ainput("What is your username? ")
        if username == "cancel":
            return False
        password = await aioconsole.ainput("What is your password? ")
        if password == "cancel":
            return False
        packet = communication.LoginRequest()
        packet.username = username
        packet.password = password
        print("Please wait...")
        # send the request to the server
        await websocket.send(packet.json)
        response = communication.Result()
        response.json = await websocket.recv()
        if response.result:
            print("Login successful!")
            return True
        else:
            # the server denied the request, let the user know and give them a second chance
            print("Denied! Please try again...")
            print(f"The server said: {response.reason}")

async def main():
    # warn about running on windows
    if os.name == "nt":
        print("Hey! it looks like you are running on Windows.")
        print(
            f"if {BLUE}THIS TEXT{NORMAL} does not display in blue, then you will need to use a different terminal")
        print(
            "A popular supported terminal is Windows Terminal, which is available on the Microsoft Store")
        print()

    # connect and log in or sign up to the server
    global serverAddress
    serverAddress = input(
        "Please enter the IP address or domain name of the server you wish to connect to: ")
    print("Does this server support encryption?")
    print("For the official homeserver, the answer is yes, otherwise, check with your homeserver administrator.")
    print("If you are unsure, choose no.")
    answer = await aioconsole.ainput("Please answer with Y or N: ")
    if answer.lower() == "y":
        protocol = "wss"
    else:
        protocol = "ws"
    print("Please wait while we attempt to connect to the server...")
    if ":" in serverAddress:  # if a port is supplied
        fullAddress = f"{protocol}://{serverAddress}"
    else:  # a port was not supplied
        fullAddress: str
        try:  # try to get the port through a DNS query
            answer = dns.resolver.resolve(
                f"_relink._tcp.{serverAddress}", "SRV")
            rrset = answer.rrset
            if rrset is None:
                raise Exception
            record = rrset.pop()
            port = record.port
            serverAddress = str(record.target).rstrip(".")
            fullAddress = f"{protocol}://{serverAddress}:{port}"
        except Exception as e:
            # the query failed, assume default port
            if protocol == "wss":
                port = 443
            else:
                port = 8765
            fullAddress = f"{protocol}://{serverAddress}:{port}"
    try:
        # connect to the server
        print(fullAddress)
        async with websockets.client.connect(fullAddress) as websocket:
            while True:
                # prompt the user
                action = await aioconsole.ainput(
                    "Log in or sign up? Type 1 for login or 2 for sign up: ")
                if action.lower() == "2" or action.lower() == "s":  # sign up
                    result = await signup(websocket)
                elif action.lower() == "1" or action.lower() == "l":  # log in
                    result = await login(websocket)
                else:
                    continue
                if result == True:
                    break
                else:
                    continue

            # we are now fully logged into the server, start the main script
            PktRcvTask = asyncio.create_task(PacketReceiver(websocket))
            InputManTask = asyncio.create_task(inputmanager(websocket))
            global WelcomeNotSent
            WelcomeNotSent = True
            renderText()  # render the screen for the first time
            # both of these loop forever, so technically we do not need to wait for both of them
            await PktRcvTask
            await InputManTask
    except websockets.exceptions.ConnectionClosedOK:
        print(f"{YELLOW}The connection has been closed.{NORMAL}")

asyncio.run(main())
