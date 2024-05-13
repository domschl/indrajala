import logging
from nicegui import ui
import os
import asyncio
import json

from indralib.indra_client import IndraClient
from indralib.server_config import Profiles


    # ------------------ GUI ------------------

class AdminGui:
    def __init__(self):
        self.profiles = Profiles()
        self.profile = None
        self.profile_name = None
        self.username = "admin"
        self.password = None
        self.cl = None
        self.session_id = None
        self.new_server_index = 1

    async def on_new_server(self):
        if len(self.profiles.profiles) > 0:
            caa = self.profiles.profiles[0]["ca_authority"]
        else:
            caa = ""
        new_server = {
            "name": f"New Server {self.new_server_index}",
            "host": "localhost",
            "port": 8080,
            "TLS": True,
            "ca_authority": caa,
        }
        self.new_server_index += 1
        self.profiles.profiles.append(new_server)
        self.profiles.save_profiles()
        ui.notify(f"New server profile {new_server['name']} added", type="info")
        self.server_grid.update()

    async def on_delete_server(self):
        row = await self.server_grid.get_selected_row()
        if row is None:
            ui.notify("No server selected", type="error")
            return
        server_name = row["name"]
        for i, server in enumerate(self.profiles.profiles):
            if server["name"] == server_name:
                self.profiles.profiles.pop(i)
                break
        self.profiles.save_profiles()
        ui.notify(f"Server profile {server_name} deleted", type="info")
        self.server_grid.update()

    async def on_changed_servers(self, e):
        changed_index = e.args["rowIndex"]
        print(f"Changed index: {changed_index}, new data: {e.args['data']}")
        self.profiles.profiles[changed_index] = e.args["data"]
        self.profiles.save_profiles()
        ui.notify(f"Server profile {self.profiles.profiles[changed_index]["name"]} updated", type="info")
        self.server_grid.update()

    async def on_default_server(self):
        row = await self.server_grid.get_selected_row()
        if row is None:
            ui.notify("No server selected", type="error")
            return
        server_name = row["name"]
        self.profiles.default_profile = server_name
        self.profiles.save_profiles()
        ui.notify(f"Default server set to {server_name}", type="info")
        self.server_grid.update()

    async def on_test_server(self):
        print("Testing server")
        row = await self.server_grid.get_selected_row()
        if row is None:
            ui.notify("No server selected", type="error")
            return
        server_name = row["name"]
        print(f"Testing server {server_name}")
        profile = self.profiles.get_profile(server_name)
        cl = IndraClient(profile=profile, verbose=True)
        ws = await cl.init_connection()
        if ws is not None:
            ui.notify(f"Connected to server {server_name} OK - Disconnecting.", type="info")
            await cl.close_connection()
            return
        else:
            ui.notify(f"Failed to connect to server {server_name} at {row['host']}", type="error")
            return

    async def do_login(self, dialog, profile_name, username, password):
        print(f"Logging in as {username} with to server {profile_name}")
        profile = self.profiles.get_profile(profile_name)
        print(f"Profile: {profile}")
        self.cl = IndraClient(profile, verbose=True)
        ws = await self.cl.init_connection()
        if ws is not None:
            ui.notify(f"Connected to server {profile_name} OK", type="info")
            self.session_id = await self.cl.login_wait(username, password)
            if self.session_id is not None:
                self.profile_name = profile_name
                self.profile = profile
                ui.notify(f"Logged in to server {profile_name} as user {username}, OK", type="info")
                dialog.submit(True)
                return
            else:
                ui.notify(f"Failed to login to server {profile_name}", type="error")
        else:
            ui.notify(f"Failed to connect to server {profile_name}", type="error")

    async def do_new_user(self, dialog, uname, pwd1, pwd2):
        # Check if user exists
        repl = await self.cl.kv_read_wait(f"entity/indrajala/user/{uname}/password")
        if repl != []:
            ui.notify(f"User {uname} already exists", type="error")
            return
        if pwd1 != pwd2:
            ui.notify("Passwords do not match", type="error")
            return
        print(f"Creating user {uname} with password {pwd1}")
        repl = await self.cl.kv_write_wait(f"entity/indrajala/user/{uname}/password", pwd1)
        print(repl)
        repl = await self.cl.kv_write_wait(f"entity/indrajala/user/{uname}/roles", "user")
        print(repl)
        ui.notify(f"User {uname} created", type="info")
        dialog.submit(True)

    async def on_new_user(self, usr_list):
        print("New user")
        new_usr=""
        pwd1=""
        pwd2=""
        with ui.dialog() as dialog, ui.card():
            ui.label("New Indrajala server user")
            ui.input(
                label="Username",
                value=new_usr,
            )
            ui.input(
                label="Password",
                value=pwd1,
                password=True,
                password_toggle_button=True,
            )
            ui.input(
                label="Password (repeat)",
                value=pwd2,
                password=True,
                password_toggle_button=True,
            )
            with ui.row():
                ui.button("Cancel", on_click=lambda: dialog.submit(None))
            ui.button("Create", on_click=lambda: self.do_new_user(dialog, new_usr, pwd1, pwd2))

            result = await dialog
            print(f"Dialog result: {result}")
            
            if result is not None:
                if result['password'] != result['password2']:
                    ui.notify("Passwords do not match", type="error")
                else:
                    print(f"Creating user {result['username']} with password {result['password']}")
                    repl = await self.cl.kv_write_wait(f"entity/indrajala/user/{result['username']}/password", result['password'])
                    print(repl)
                    repl = await self.cl.kv_write_wait(f"entity/indrajala/user/{result['username']}/roles", "user")
                    print(repl)
                    ui.notify(f"User {result['username']} created", type="info")
            else:
                return

    async def on_delete_user(self):
        print("Delete user")

    async def on_change_password(self):
        print("Change password")
        
    def login_gui(self, servers, default_server, default_username, default_password):
        username = default_username
        password = default_password
        with ui.dialog() as dialog, ui.card():
            ui.label("Login to Indrajala server")
            server_ui = ui.select(servers, value=default_server, label="Server") # , on_change=lambda e: set_server(e))
            uname = ui.input(
                label="Username",
                value=username,
                # on_change=lambda e: set_username(e),
            )
            pwd = ui.input(
                label="Password",
                value=password,
                password=True,
                password_toggle_button=True,
                # on_change=lambda e: set_password(e),
            )
            with ui.row():
                ui.button("Cancel", on_click=lambda: dialog.submit(None))
                ui.button("Login", on_click=lambda: self.do_login(dialog, server_ui.value, uname.value, pwd.value))
            return dialog
    
    async def on_login(self):
        servers = [p['name'] for p in self.profiles.profiles]
        profile_name = self.profiles.default_profile
        print(servers, profile_name)
        username = "admin"
        password = None
        dialog = self.login_gui(servers, profile_name, username, password)
        result = await dialog
        print(f"Dialog result: {result}")
        return result

    async def on_logout(self):
        if self.session_id is None:
            ui.notify("Not logged in", type="error")
            return
        if self.cl is not None:
            await self.cl.logout()
            await self.cl.close_connection()
        ui.notify("Logged out")

    async def user_list(self):
        if self.cl is None or self.session_id is None:
            ui.notify("Not logged in", type="error")
            return
        repl = await self.cl.kv_read_wait("entity/indrajala/user/%")
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
        await self.cl.kv_delete("entity/indrajala/user_columns")

        user_columns = await self.cl.kv_read_wait("entity/indrajala/user_columns")
        print(user_columns)
        if user_columns == []:
            user_columns = [("username", "User name"), ("roles", "Roles")]
            await self.cl.kv_write_wait("entity/indrajala/user_columns", json.dumps(user_columns))
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
                ui.button("New User", on_click=self.on_new_user)
                ui.button("Delete User", on_click=self.on_delete_user)
                ui.button("Change password", on_click=self.on_change_password)

    def server_list(self):
        server_column_defs = [
            {
                "headerName": "Name",
                "field": "name",
                "editable": True,
                # "checkboxSelection": True,
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
        with ui.expansion('Server profiles', icon='computer').classes('w-full'):
            self.server_grid = ui.aggrid(
                {
                    "columnDefs": server_column_defs,
                    "rowData": self.profiles.profiles,
                    "rowSelection": "single",
                }
            ).classes("max-h-40")
            self.server_grid.on("cellValueChanged", self.on_changed_servers)
            with ui.row():
                ui.button(
                    "New Server",
                    on_click=self.on_new_server,
                )
                ui.button("Delete Server", on_click=self.on_delete_server)
                ui.button("Default Server", on_click=self.on_default_server)
                ui.button("Test Server", on_click=self.on_test_server)

    def login_state(self):
        ui.separator()
        with ui.row():
            ui.button("Login", on_click=self.on_login)
            ui.button("Logout", on_click=self.on_logout)

    def user_state(self):
        ui.separator()
        ui.button("User list", on_click=self.user_list)

    def run(self):
        # ui.title("Indrajala Admin")
        self.server_list()
        self.login_state()
        self.user_state()
        # self.server_grid

        ui.run(port=8081, host="localhost")


if __name__ == "__main__" or __name__ == "__mp_main__":
    admin_gui = AdminGui()
    admin_gui.run()
