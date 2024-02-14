import asyncio
import os
import sys
import getpass

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


async def main():
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
    if cl is not None:
        if session_id is not None:
            await cl.logout_wait()
            print("Logged out.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting...")
