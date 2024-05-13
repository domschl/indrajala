import logging
from nicegui import ui
import os
import asyncio
import json

from indralib.indra_client import IndraClient
from indralib.server_config import Profiles


    # ------------------ GUI ------------------

class AdminGuiOld:
    def __init__(self):
        self.profiles = Profiles()
        self.profile = None
        self.profile_name = self.profiles.default_profile
        if self.profile_name is None or self.profile_name == "":
            if len(self.profiles.profiles) > 0:
                self.profile = self.profiles.profiles[0]
                self.profile_name = self.profile["name"]
            else:
                self.profile_name = None
        else:
            for p in self.profiles.profiles:
                if p["name"] == self.profile_name:
                    self.profile = p
                    break
            if self.profile is None:
                if len(self.profiles.profiles) > 0:
                    self.profile = self.profiles.profiles[0]
                    self.profile_name = self.profile["name"]
                else:
                    self.profile_name = None
        self.username = self.profiles.default_username
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
        if self.profiles.default_profile == server_name:
            self.profiles.default_profile = ""
            self.profile_name = ""
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
        self.user_list_gui()
        self.user_grid.update()

        if self.cl is None or self.session_id is None:
            ui.notify("Not logged in", type="error")
            return
        repl = await self.cl.kv_read_wait("entity/indrajala/user/%")
        print(repl)
        self.users = []
        for r in repl:
            usertoks = r[0].split("/")
            value = r[1]
            if len(usertoks) == 5:
                user = usertoks[3]
                prop = usertoks[4]
                if user not in self.users:
                    self.users.append({'username': user, prop: value})
                else:
                    for u in self.users:
                        if u['username'] == user:
                            self.users[user][prop] = value
        print(self.users)
        await self.cl.kv_delete("entity/indrajala/user_columns")

        self.user_columns = await self.cl.kv_read_wait("entity/indrajala/user_columns")
        print(user_columns)
        if user_columns == []:
            user_columns = [("username", "User name"), ("roles", "Roles")]
            await self.cl.kv_write_wait("entity/indrajala/user_columns", json.dumps(user_columns))
        else:
            self.user_columns = json.loads(user_columns[0][1])
        print(user_columns)
        print(self.users)
        self.user_column_defs = []
        for col in user_columns:
            if col == "username":
                self.user_column_defs.append({"headerName": col[1], "field": col[0], "editable": False, "hidden": True})
            else:
                self.user_column_defs.append({"headerName": col[1], "field": col[0], "editable": True})
        print(self.user_column_defs)

        self.user_grid.update()

    def user_list_gui(self):
        ui.label("Users").classes("text-h4")
        self.user_grid = ui.aggrid(
            {
                "columnDefs": self.user_column_defs,
                "rowData": self.users,
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
        # with ui.expansion('Server profiles', icon='computer').classes('w-full'):
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
        with ui.row():
            ui.button("Login", on_click=self.on_login)
            ui.button("Logout", on_click=self.on_logout)

    def run(self):
        # ui.title("Indrajala Admin")
        self.login_state()
        ui.separator()
        with ui.splitter(value=10).classes('w-full h-full') as splitter:
            with splitter.before:
                with ui.tabs().props('vertical').classes('w-full') as tabs:
                    self.servers_tab = ui.tab('Servers', icon='computer')
                    self.users_tab = ui.tab('Users', icon='group')
            with splitter.after:
                with ui.tab_panels(tabs, value=self.servers_tab) \
                        .props('vertical').classes('w-full h-full'):
                    with ui.tab_panel(self.servers_tab):
                        ui.label('Servers').classes('text-h4')
                        self.server_list()
                    with ui.tab_panel(self.users_tab):
                        ui.label('Users').classes('text-h4')
                        self.user_list()

class ServerEditorGui:
    def __init__(self):
        self.profiles = Profiles()
        self.profile_name = self.profiles.default_profile
        if self.profile_name is None or self.profile_name == "":
            if len(self.profiles.profiles) > 0:
                self.profile_name = self.profiles.profiles[0]["name"]
            else:
                self.profile_name = None
        else:
            found = False
            for p in self.profiles.profiles:
                if p["name"] == self.profile_name:
                    found = True
                    break
            if not found:
                self.profile_name = None
            if self.profile_name is None:
                if len(self.profiles.profiles) > 0:
                    self.profile_name = self.profiles.profiles[0]["name"]
                else:
                    self.profile_name = None
        self.cl = None
        self.session_id = None
        self.new_server_index = 1

        self.server_gui_list = None

    def get_current_profile(self):
        for p in self.profiles.profiles:
            if p["name"] == self.profile_name:
                return p
        return None

    def get_server_list(self):
        return [p["name"] for p in self.profiles.profiles]
    
    def add_change_server(self, name, host, port, tls, ca_authority):
        new_server = {
            "name": name,
            "host": host,
            "port": port,
            "TLS": tls,
            "ca_authority": ca_authority,
        }
        # Check if server already exists
        for i, server in enumerate(self.profiles.profiles):
            if server["name"] == name:
                self.profiles.profiles[i] = new_server
                self.profiles.save_profiles()
                return new_server
        self.profiles.profiles.append(new_server)
        self.profiles.save_profiles()
        return new_server
    
    def delete_server(self, name):
        for i, server in enumerate(self.profiles.profiles):
            if server["name"] == name:
                self.profiles.profiles.pop(i)
                break
        if self.profiles.default_profile == name:
            self.profiles.default_profile = ""
            self.profile_name = ""
        self.profiles.save_profiles()

    def set_default_server(self, name):
        for i, server in enumerate(self.profiles.profiles):
            if server["name"] == name:
                self.profiles.default_profile = name
                self.profiles.save_profiles()
                return True
        return False

    async def check_server(self, name):
        profile = self.profiles.get_profile(name)
        if profile is None:
            return False
        cl = IndraClient(profile=profile, verbose=True)
        ws = await cl.init_connection()
        if ws is not None:
            await cl.close_connection()
            self.profile_name = name
            self.profiles.save_profiles()
            return True
        return False
    
    async def on_new_server(self):
        with ui.dialog() as dialog, ui.card():
            ui.label("New server profile")
            ns_name = ui.input(label="Name", value=f"New Server {self.new_server_index}")
            ns_host = ui.input(label="Host", value="localhost")
            ns_port = ui.input(label="Port", value=8080)
            ns_tls = ui.checkbox("TLS", value=True)
            ns_ca = ui.input(label="CA Authority", value="")
            with ui.row():
                ui.button("Cancel", on_click=lambda: dialog.submit(None))
                ui.button("Create", on_click=lambda: dialog.submit((ns_name.value, ns_host.value, ns_port.value, ns_tls.value, ns_ca.value)))
            res = await dialog
            if res is not None:
                name = res[0]
                host = res[1]
                port = res[2]
                tls = res[3]
                ca_authority = res[4]
                self.add_change_server(name, host, port, tls, ca_authority)
                self.server_gui_list.update()
                self.new_server_index += 1

    async def on_edit_server(self):
        if self.current_profile is None:
            ui.notify("No server selected", type="error")
            return
        server = self.profiles.get_profile(self.current_profile)
        with ui.dialog() as dialog, ui.card():
            ui.label("Edit profile")
            ns_name = ui.input(label="Name", value=server['name'])
            ns_host = ui.input(label="Host", value=server['host'])
            ns_port = ui.input(label="Port", value=server['port'])
            ns_tls = ui.checkbox("TLS", value=server['TLS'])
            ns_ca = ui.input(label="CA Authority", value=server['ca_authority'])
            with ui.row():
                ui.button("Cancel", on_click=lambda: dialog.submit(None))
                ui.button("Save", on_click=lambda: dialog.submit((server['name'], ns_name.value, ns_host.value, ns_port.value, ns_tls.value, ns_ca.value)))
            res = await dialog
            if res is not None:
                old_name = res[0]
                name = res[1]
                host = res[2]
                port = res[3]
                tls = res[4]
                ca_authority = res[5]
                if old_name != name:
                    self.delete_server(old_name)
                    ui.notify(f"Server profile {old_name} deleted", type="info")
                self.add_change_server(name, host, port, tls, ca_authority)
                ui.notify(f"Server profile {name} updated", type="info")
                self.server_gui_list.update()

    async def on_delete_server(self):
        if self.current_profile is None:
            ui.notify("No server selected", type="error")
            return
        server_name = self.current_profile
        
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Delete server profile {server_name}")
            ui.label(f"Are you sure you want to delete the server profile {server_name}?")
            with ui.row():
                ui.button("Cancel", on_click=lambda: dialog.submit(False))
                ui.button("Delete", on_click=lambda: dialog.submit(True))
            res = await dialog
            if res is True:
                ui.notify(f"Server profile {server_name} deleted", type="info")
                self.delete_server(server_name)
                self.server_gui_list.update()
            else:
                ui.notify(f"Server profile {server_name} not deleted", type="info")

    async def on_check_server(self):
        if self.current_profile is None:
            ui.notify("No server selected", type="error")
            return
        if await self.check_server(self.current_profile):
            ui.notify(f"Connected to server {self.profile_name} OK - Set as default", type="info")
            return
        else:
            ui.notify(f"Failed to connect to server {self.current_profile}", type="error")
            return

    async def on_server_selected(self):
        row = await self.server_gui_list.get_selected_row()
        if row is None:
            self.current_profile = None
            return
        self.current_profile = row['name']
        ui.notify(f'Selected server {row['name']}', type='info')

    def server_list_gui(self):
        self.current_profile = None  ### XXX
        columnDefs = [
            {'headerName': 'Server Name', 'field': 'name', 'checkboxSelection': True},
            {'headerName': 'Host', 'field': 'host'},
            {'headerName': 'Port', 'field': 'port'},
            {'headerName': 'TLS', 'field': 'TLS'},
            # {'headerName': 'CA Authority', 'field': 'ca_authority'},
        ]
        self.server_gui_list = ui.aggrid({'columnDefs': columnDefs, 'rowData': self.profiles.profiles, 'selection': 'single'}) # , on_select=self.on_server_selected)
        self.server_gui_list.on('selectionChanged', self.on_server_selected)

        self.server_buttons = ui.row()
        with self.server_buttons:
            self.add_button = ui.button(icon='add', on_click=self.on_new_server)
            self.edit_button = ui.button(icon='edit', on_click=self.on_edit_server)
            self.edit_button.bind_enabled_from(self, 'current_profile')
            self.check_button = ui.button(icon='check', on_click=self.on_check_server)
            self.check_button.bind_enabled_from(self, 'current_profile')
            self.delete_button = ui.button(icon='delete', on_click=self.on_delete_server)
            self.delete_button.bind_enabled_from(self, 'current_profile')


class UserEditorGui:
    def __init__(self):
        self.users = []
        self.current_user = None
        self.cl = None
        self.session_id = None

    async def on_new_user(self):
        pass

    async def on_edit_user(self):
        pass

    async def on_delete_user(self):
        pass

    async def on_password_user(self):
        pass

    async def on_login(self):
        pass

    async def on_logout(self):
        pass

    async def on_user_selected(self):
        pass

    def user_list_gui(self):
        self.current_user = None  ### XXX
        columnDefs = [
            {'headerName': 'User Name', 'field': 'name', 'checkboxSelection': True},
            {'headerName': 'Role', 'field': 'role'},
        ]
        self.users = []
        self.user_gui_list = ui.aggrid({'columnDefs': columnDefs, 'rowData': self.users, 'selection': 'single'}) # , on_select=self.on_user_selected)
        self.user_buttons = ui.row()
        with self.user_buttons:
            self.add_button = ui.button(icon='add', on_click=self.on_new_user)
            self.add_button.bind_enabled_from(self, 'session_id')
            self.edit_button = ui.button(icon='edit', on_click=self.on_edit_user)
            self.edit_button.bind_enabled_from(self, 'current_user')
            self.password_button = ui.button(icon='password', on_click=self.on_password_user)
            self.password_button.bind_enabled_from(self, 'current_user')
            self.delete_button = ui.button(icon='delete', on_click=self.on_delete_user)
            self.delete_button.bind_enabled_from(self, 'current_user')


class AdminGui:
    def __init__(self):
        self.server_editor = ServerEditorGui()
        self.user_editor = UserEditorGui()
        self.header_status = ui.row()
        with self.header_status:
            with ui.splitter() as splitter:
                with splitter.before:
                    ui.label("Indrajala Admin").classes('text-h4')
                with splitter.after:
                    with ui.column().classes('ml-2'):
                        with ui.row():
                            ui.label("Server: ")
                            self.label = ui.label().classes('text-bold')
                            self.label.bind_text_from(self.server_editor, 'profile_name')
                        # with ui.row():
                            ui.label("User: ")
                            self.label = ui.label().classes('text-bold')
                            self.label.bind_text_from(self.server_editor, 'username')
                        with ui.row():
                            self.login_button = ui.button(icon="login", on_click=self.user_editor.on_login)
                            self.login_button.bind_enabled_from(self.server_editor, 'profile_name')
                            self.logout_button = ui.button(icon="logout", on_click=self.user_editor.on_logout)
                            self.logout_button.bind_enabled_from(self.user_editor, 'session_id')
        with ui.splitter(value=10).classes('w-full h-full') as splitter:
            with splitter.before:
                with ui.tabs().props('vertical').classes('w-full') as tabs:
                    self.servers_tab = ui.tab('Servers', icon='computer')
                    self.users_tab = ui.tab('Users', icon='group')
            with splitter.after:
                with ui.tab_panels(tabs, value=self.servers_tab) \
                        .props('vertical').classes('w-full h-full'):
                    with ui.tab_panel(self.servers_tab):
                        ui.label('Servers').classes('text-h4')
                        self.server_editor.server_list_gui()
                    with ui.tab_panel(self.users_tab):
                        ui.label('Users').classes('text-h4')
                        self.user_editor.user_list_gui()

        

    def run(self):
        ui.run(port=8090, host="localhost")


if __name__ == "__main__" or __name__ == "__mp_main__":
    admin_gui = AdminGui()
    admin_gui.run()
