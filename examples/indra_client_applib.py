import logging
import getpass

from indralib.indra_event import IndraEvent  # type: ignore
from indralib.indra_client import IndraClient  # type: ignore


async def interactive_login(
    server_profile="default",
    username=None,
    password=None,
    login_retries=3,
    verbose=False,
):
    session_id = None
    username = None
    cl = IndraClient(verbose=verbose, profile=server_profile)
    if cl is None:
        logging.error("Could not create Indrajala client")
    ws = await cl.init_connection(verbose=False)
    if ws is not None:
        if verbose:
            print("Connected.")
    else:
        cl.session_id = session_id
        cl.username = username
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
                cl.session_id = session_id
                cl.username = username
                return cl
    if verbose:
        print(f"Logged in, user: {username}, session: {session_id}")
    cl.session_id = session_id
    cl.username = username
    return cl
