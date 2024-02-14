import logging
import getpass
import os

# Add the parent directory to the path so we can import the client
import sys

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "indralib/src"
)
# print(path)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore
from indra_client import IndraClient  # type: ignore


async def interactive_login(
    server_profile="default",
    username=None,
    password=None,
    login_retries=3,
    verbose=False,
):
    session_id = None
    cl = IndraClient(verbose=verbose, profile=server_profile)
    if cl is None:
        logging.error("Could not create Indrajala client")
    ws = await cl.init_connection(verbose=False)
    if ws is not None:
        if verbose:
            print("Connected.")
    else:
        return cl
    # Get user and password either by args or by prompting:
    ret_count = 0
    while session_id is None:
        if username is None:
            username = input("Username: ")
        if password is None:
            password = getpass.getpass("Password: ")
        session_id = await cl.login_wait(username, password)
        if session_id is None:
            if verbose:
                print("Login failed")
            username = None
            password = None
            ret_count += 1
            if ret_count >= login_retries:
                if verbose:
                    print("Too many retries, exiting.")
                return cl
    if verbose:
        print(f"Logged in, user: {username}, session: {session_id}")
    return cl
