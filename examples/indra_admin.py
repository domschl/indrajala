import logging
from nicegui import ui
import os
import asyncio
import json

from indralib.indra_client import IndraClient
from indralib.server_config import Profiles


    # ------------------ GUI ------------------


new_server_index = 1

column_defs = [
    # {
    #     "headerName": "Default",
    #     "field": "default",
    #     "editable": True,
    #     "width": 80,
    # },
    {
        "headerName": "Name",
        "field": "name",
        "editable": True,
        "checkboxSelection": True,
    },
    {"headerName": "Host", "field": "host", "editable": True},
    {"headerName": "Port", "field": "port", "editable": True},
    {"headerName": "TLS", "field": "TLS", "editable": True},
    {
        "headerName": "CA Authority",
        "field": "ca_authority",
        "editable": True,
    },
]


async def new_server():
    global new_server_index
    if len(profiles.profiles) > 0:
        caa = profiles.profiles[0]["ca_authority"]
    else:
        caa = ""
    new_server = {
        "name": f"New Server {new_server_index}",
        "host": "localhost",
        "port": 8080,
        "TLS": True,
        "ca_authority": caa,
    }
    new_server_index += 1
    profiles.profiles.append(new_server)
    profiles.save_profiles()
    ui.notify(f"New server profile {new_server['name']} added", type="info")
    sg.update()


async def delete_server():
    row = await sg.get_selected_row()
    if row is None:
        ui.notify("No server selected", type="error")
        return
    server_name = row["name"]
    for i, server in enumerate(profiles.profiles):
        if server["name"] == server_name:
            profiles.profiles.pop(i)
            break
    profiles.save_profiles()
    ui.notify(f"Server profile {server_name} deleted", type="info")
    sg.update()


async def changed_servers(e):
    changed_index = e.args["rowIndex"]
    print(f"Changed index: {changed_index}, new data: {e.args['data']}")
    profiles.profiles[changed_index] = e.args["data"]
    profiles.save_profiles()
    ui.notify(f"Server profile {profiles.profiles[changed_index]["name"]} updated", type="info")
    sg.update()


async def default_server():
    row = await sg.get_selected_row()
    if row is None:
        ui.notify("No server selected", type="error")
        return
    server_name = row["name"]
    profiles.default_profile = server_name
    profiles.save_profiles()
    ui.notify(f"Default server set to {server_name}", type="info")
    sg.update()

async def test_server():
    print("Testing server")
    row = await sg.get_selected_row()
    if row is None:
        ui.notify("No server selected", type="error")
        return
    server_name = row["name"]
    print(f"Testing server {server_name}")
    profile = profiles.get_profile(server_name)
    cl = IndraClient(profile=profile, verbose=True)
    ws = await cl.init_connection()
    if ws is not None:
        ui.notify(f"Connected to server {server_name} OK - Disconnecting.", type="info")
        await cl.close_connection()
        return
    else:
        ui.notify(f"Failed to connect to server {server_name} at {row['host']}", type="error")
        return

profiles = Profiles()
profile = None
profile_name = None
username = "admin"
password = None
cl = None
session_id = None


def set_username(e):
    global username
    print(f"Setting username to {e.value}")
    username = e.value

def set_password(e):
    global password
    print(f"Setting password to {e.value}")
    password = e.value

def set_server(e):
    global profile_name
    print(f"Setting server to {e.value}")
    profile_name = e.value

async def do_login(dialog):
    global cl
    global session_id
    print(f"Logging in as {username} with password {password} to server {profile_name}")
    profile = profiles.get_profile(profile_name)
    print(f"Profile: {profile}")
    cl = IndraClient(profile, verbose=True)
    ws = await cl.init_connection()
    if ws is not None:
        ui.notify(f"Connected to server {profile_name} OK", type="info")
        session_id = await cl.login_wait(username, password)
        if session_id is not None:
            ui.notify(f"Logged in to server {profile_name} as user {username}, OK", type="info")
            dialog.submit((cl, session_id, profile, username, password, profile_name))
            return
        else:
            ui.notify(f"Failed to login to server {profile_name}", type="error")
    else:
        ui.notify(f"Failed to connect to server {profile_name}", type="error")

async def new_user():
    print("New user")

async def delete_user():
    print("Delete user")

async def user_password():
    print("Change password")
    
async def login_gui(servers, default_server, username, password):
    with ui.dialog() as dialog, ui.card():
        ui.label("Login to Indrajala server")
        ui.select(servers, value=default_server, label="Server", on_change=lambda e: set_server(e))
        ui.input(
            label="Username",
            value=username,
            on_change=lambda e: set_username(e),
        )
        ui.input(
            label="Password",
            value=password,
            password=True,
            password_toggle_button=True,
            on_change=lambda e: set_password(e),
        )
        with ui.row():
            ui.button("Cancel", on_click=lambda: dialog.submit(None))
            ui.button("Login", on_click=lambda: do_login(dialog))

        result = await dialog
        print(f"Dialog result: {result}")
        return result

async def login():
    global profile_name
    servers = [p['name'] for p in profiles.profiles]
    profile_name = profiles.default_profile
    print(servers, default_server)
    await login_gui(servers, profile_name, username, password)

async def logout():
    global cl
    if session_id is None:
        ui.notify("Not logged in", type="error")
        return
    await cl.logout()
    if cl is not None:
        await cl.close_connection()
    ui.notify("Logged out")

async def user_list():
    if cl is None or cl.session_id is None:
        ui.notify("Not logged in", type="error")
        return
    repl = await cl.kv_read_wait("entity/indrajala/user/%")
    print(repl)
    users = []
    for r in repl:
        usertoks = r[0].split("/")
        value = r[1]
        if len(usertoks) == 5:
            user = usertoks[3]
            prop = usertoks[4]

            if user not in users:
                users.append({'username': user, prop: value})
            else:
                for u in users:
                    if u['username'] == user:
                        u[prop] = value
    print(users)
    
    await cl.kv_delete("entity/indrajala/user_columns")

    user_columns = await cl.kv_read_wait("entity/indrajala/user_columns")
    print(user_columns)
    if user_columns == []:
        user_columns = [("username", "User name"), ("roles", "Roles")]
        await cl.kv_write_wait("entity/indrajala/user_columns", json.dumps(user_columns))
    else:
        user_columns = json.loads(user_columns[0][1])
    print(user_columns)
    print(users)
    user_column_defs = []
    for col in user_columns:
        if col == "username":
            user_column_defs.append({"headerName": col[1], "field": col[0], "editable": False, "hidden": True})
        else:
            user_column_defs.append({"headerName": col[1], "field": col[0], "editable": True})
    print(user_column_defs)
    with ui.expansion('User list', icon='people').classes('w-full'):
        ug = ui.aggrid(
            {
                "columnDefs": user_column_defs,
                "rowData": users,
                "rowSelection": "single",
            }
        ).classes("max-h-40")
        # ug.on("cellValueChanged", changed_users)
        with ui.row():
            ui.button("New User", on_click=new_user)
            ui.button("Delete User", on_click=delete_user)
            ui.button("Change password", on_click=user_password)


with ui.expansion('Server profiles', icon='computer').classes('w-full'):
    sg = ui.aggrid(
        {
            "columnDefs": column_defs,
            "rowData": profiles.profiles,
            "rowSelection": "single",
        }
    ).classes("max-h-40")
    sg.on("cellValueChanged", changed_servers)

    with ui.row():
        ui.button(
            "New Server",
            on_click=new_server,
        )
        ui.button("Delete Server", on_click=delete_server)
        ui.button("Default Server", on_click=default_server)
        ui.button("Test Server", on_click=test_server)

ui.separator()
with ui.row():
    ui.button("Login", on_click=login)
    ui.button("Logout", on_click=logout)

ui.separator()
ui.button("User list", on_click=user_list)



ui.run(port=8081, host="localhost")
