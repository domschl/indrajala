import asyncio
import logging
import os
import aioconsole

# Add the parent directory to the path so we can import the client
import sys

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "indralib/src"
)
print(path)
sys.path.append(path)
from indra_event import IndraEvent
from indra_client import IndraClient

# Terminal control codes for formatting
CLEAR_SCREEN = "\033[2J\033[H"  # Clear screen
MOVE_CURSOR_UP = "\033[F"  # Move cursor up one line
ERASE_LINE = "\033[K"  # Erase current line

# Message history lists
remote_message_history = []
local_message_history = []


async def receive_remote(cl):
    while True:
        ie = await cl.recv_event()
        if ie is None:
            remote_message = ""
        else:
            msg = ie.data
            remote_message = msg
        remote_message_history.append(remote_message)
        if len(remote_message_history) > 10:
            remote_message_history.pop(
                0
            )  # Remove oldest message if history exceeds 10 lines
        display_output()


async def receive_io():
    while True:
        local_message = await aioconsole.ainput("Enter your message: ")
        local_message_history.append(local_message)
        if len(local_message_history) > 5:
            local_message_history.pop(
                0
            )  # Remove oldest message if history exceeds 5 lines

        display_output()


def display_output():
    print(CLEAR_SCREEN)

    # Display remote message history
    print("Remote messages:")
    for message in remote_message_history[-10:]:
        print(f"{message}")

    # Display local message history
    print("\nYour messages:")
    for message in local_message_history[-5:]:
        print(f"{message}")


async def chat():
    cl = IndraClient(config_file="ws_indra.toml", verbose=False)
    if cl is None:
        logging.error("Could not create Indrajala client")
        return
    ws = await cl.init_connection(verbose=True)
    if ws is None:
        logging.error("Could not connect to Indrajala")
        return
    await cl.subscribe(["CHAT.1/#"])

    print(CLEAR_SCREEN)
    await asyncio.gather(receive_remote(cl), receive_io())


logging.basicConfig(level=logging.INFO)
try:
    asyncio.get_event_loop().run_until_complete(chat())
except KeyboardInterrupt:
    pass
