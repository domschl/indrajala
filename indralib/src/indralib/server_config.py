import json
import os
import logging


class Profiles:
    def __init__(self):
        self.log = logging.getLogger("indralib.server_config")
        self.profiles = []
        self.profile_file = os.path.expanduser("~/.config/indrajala/servers.json")
        if not os.path.exists(os.path.dirname(self.profile_file)):
            os.makedirs(os.path.dirname(self.profile_file))
        if not os.path.exists(self.profile_file):
            with open(self.profile_file, "w") as f:
                f.write(
                    json.dumps(
                        {
                            "profiles": [],
                            "default_profile": "",
                            "default_username": "admin",
                            "default_password": None,
                            "auto_login": False,
                        },
                        indent=4,
                    )
                )
        with open(self.profile_file, "rb") as f:
            try:
                raw_profiles = json.load(f)
            except Exception as e:
                print(f"Error reading profiles: {e}")
                raw_profiles = {
                    "profiles": [],
                    "default_profile": "",
                    "default_username": "admin",
                    "default_password": None,
                    "auto_login": False,
                }
        for index, profile in enumerate(raw_profiles["profiles"]):
            if not Profiles.check_profile(profile):
                self.log.error(f"Invalid profile: {profile} in {self.profile_file}")
                del raw_profiles["profiles"][index]
        self.profiles = raw_profiles["profiles"]
        self.default_profile = raw_profiles["default_profile"]
        self.default_username = raw_profiles["default_username"]
        self.default_password = raw_profiles["default_password"]
        self.auto_login = raw_profiles["auto_login"]

    def get_profiles(self):
        return self.profiles

    def get_default_profile(self):
        return self.get_profile(self.default_profile)

    def get_profile(self, profile_name):
        for profile in self.profiles:
            if profile["name"] == profile_name:
                return profile
        return None

    @staticmethod
    def check_profile(profile):
        mandatory_keys = ["host", "port", "TLS", "name"]
        for key in mandatory_keys:
            if key not in profile:
                return False
        optional_keys = ["ca_authority"]
        for key in optional_keys:
            if key not in profile:
                profile[key] = ""
        return True

    @staticmethod
    def get_uri(profile):
        uri = "ws"
        if profile.get("TLS", False):
            uri += "s"
        uri += f"://{profile['host']}:{profile['port']}/ws"
        return uri

    def save_profiles(self):
        # check for duplicate names
        names = []
        for profile in self.profiles:
            while profile["name"] in names:
                new_name = profile["name"] + " (copy)"
                self.log.warning(
                    f"Duplicate profile name: {profile['name']}, changing to {new_name}"
                )
                profile["name"] = new_name
            names.append(profile["name"])
        raw_profiles = {
            "profiles": self.profiles,
            "default_profile": self.default_profile,
            "default_username": self.default_username,
            "default_password": self.default_password,
            "auto_login": self.auto_login,
        }
        with open(self.profile_file, "w") as f:
            try:
                json.dump(raw_profiles, f, indent=4)
            except Exception as e:
                self.log.error(f"Error saving profiles: {e}")
