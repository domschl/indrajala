import asyncio
import os
import sys
import logging

import aioconsole

# Add the parent directory to the path so we can import the client
import sys

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "indralib/src"
)
# print(path)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore
from indra_client import IndraClient  # type: ignore

from indra_client_applib import interactive_login


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
        print("RECEIVE", ie)
        if ie is None:
            remote_message = ""
        else:
            msg = ie.data
            remote_message = msg.replace("###", "")
            if remote_message[-1] == "}":
                remote_message = remote_message[:-1]
                nl = True
            else:
                nl = False
        if len(remote_message_history) == 0:
            remote_message_history.append(remote_message)
        elif len(remote_message_history[-1] + remote_message) < 80:
            remote_message_history[-1] += remote_message
            if nl:
                remote_message_history.append("")
        else:
            remote_message_history.append(remote_message)
            if nl:
                remote_message_history.append("")
        if len(remote_message_history) > 10:
            remote_message_history.pop(
                0
            )  # Remove oldest message if history exceeds 10 lines
        display_output()


async def receive_io(cl):
    while True:
        local_message = await aioconsole.ainput("Enter your message: ")
        local_message_history.append(local_message)
        if len(local_message_history) > 5:
            local_message_history.pop(
                0
            )  # Remove oldest message if history exceeds 5 lines
        ie = IndraEvent()
        ie.data = local_message
        ie.data_type = "String"
        ie.domain = f"$chat/{cl.username}"
        ie.auth_hash = cl.session_id
        await cl.send_event(ie)
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
    username = None
    password = None
    if len(sys.argv) > 1:
        username = sys.argv[1]
    if len(sys.argv) > 2:
        password = sys.argv[2]
    cl, session_id = await interactive_login(username=username, password=password)
    if session_id is None:
        esc = True
    else:
        esc = False

    if esc is True:
        return

    await cl.subscribe(["chat.1/#"])

    print(CLEAR_SCREEN)
    await asyncio.gather(receive_remote(cl), receive_io(cl))


logging.basicConfig(level=logging.INFO)
try:
    asyncio.get_event_loop().run_until_complete(chat())
except KeyboardInterrupt:
    pass
