import asyncio
import logging
import os
import sys
import getpass

import nest_asyncio

nest_asyncio.apply()

# Add the parent directory to the path so we can import the client
import sys

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "indralib/src"
)
# print(path)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore
from indra_client import IndraClient  # type: ignore


async def main():
    cl = IndraClient(verbose=False, profile="default")
    if cl is None:
        logging.error("Could not create Indrajala client")
    ws = await cl.init_connection(verbose=False)
    if ws is not None:
        print("Connected.")
    else:
        return
    # Get user and password either by args or by prompting:
    user = None
    password = None
    if len(sys.argv) > 1:
        user = sys.argv[1]
    if len(sys.argv) > 2:
        password = sys.argv[2]
    session_id = None
    while session_id is None:
        if user is None:
            user = input("User: ")
        if password is None:
            password = getpass.getpass("Password: ")
        session_id = await cl.login_wait(user, password)
        if session_id is None:
            print("Login failed")
            user = None
            password = None
    print(f"Logged in, session: {session_id}")
    esc = False
    while esc is False:
        cmd = input("InAdmin> ")
        if cmd == "quit" or cmd == "logout":
            esc = True
        else:
            cmds = cmd.split(" ")
            if cmds[0] == "adduser":
                if len(cmds) == 2 or len(cmds) == 3:
                    username = cmds[1]
                    if len(cmds) == 3:
                        password = cmds[2]
                    else:
                        password = getpass.getpass("Password: ")
                    key = f"entity/indrajala/user/{username}/password"
                    res = await cl.kv_write_wait(key, password)
                    if res is not None:
                        print(f"User {username} added: {res}")
                    else:
                        print(f"Failed to add user {username}")
                else:
                    print("Usage: adduser <username> <password>")
            elif cmds[0] == "deluser":
                if len(cmds) == 2:
                    username = cmds[1]
                    key = f"entity/indrajala/user/{username}/password"
                    res = await cl.kv_delete_wait(key)
                    if res is not None:
                        print(f"User {username} deleted: {res}")
                    else:
                        print(f"Failed to delete user {username}")
                else:
                    print("Usage: deluser <username>")
            elif cmds[0] == "test":
                ev = IndraEvent()
                ev.domain = "$trx/test"
                ev.data = "Test message"
                t_fut = await cl.send_event(ev)
                test_result = await t_fut
                print(f"Test result: {test_result.data}")
            else:
                print("Unknown command")
    await cl.logout_wait()
    print("Logged out.")


if __name__ == "__main__":
    asyncio.run(main())
