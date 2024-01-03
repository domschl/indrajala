"""
Main indrajala process
"""

import os
import logging
from logging.handlers import TimedRotatingFileHandler
import argparse
import pathlib
import importlib
import json
import time

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 and older:
    import tomli as tomllib  # type: ignore

# XXX dev only
import sys

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "indralib/src"
)
print(path)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore

INDRAJALA_VERSION = "0.1.0"


def main_runner(main_logger, modules):
    subs = {}

    for module in modules:
        default_subs = ["$cmd/quit", f"{module}/#"]
        for sub in default_subs:
            if sub not in subs[module]:
                subs[module].append(sub)

    tasks = []
    for module in modules:
        m_op = getattr(modules[module], "server_task", None)
        if callable(m_op) is True:
            pass
        main_logger.debug(f"adding task from {module}")
        tasks.append(asyncio.create_task(modules[module].get(), name=module))



def load_modules(main_logger, toml_data, args):
    modules = {}
    if "indrajala" not in toml_data:
        main_logger.error(
            f"The toml_file {args.toml_file} needs to contain a section [indrajala], cannot continue with invalid configuration."
        )
        return {}
    if "modules" not in toml_data["indrajala"]:
        main_logger.error(
            f"In toml_file {args.toml_file}, [indrajala] has no list of modules, add: modules=[..]"
        )
        return {}
    for module in toml_data["indrajala"]["modules"]:
        if module not in toml_data:
            main_logger.warning(
                f"In toml_file {args.toml_file}, no configuration section [{module}] found, skipping this module"
            )
        else:
            sub_mods = []
            single_instance = True
            if isinstance(toml_data[module], list) is True:
                sub_mods = toml_data[module]
                single_instance = False
            else:
                sub_mods = [toml_data[module]]
            main_logger.info(f"Activating module [{module}]")
            try:
                main_logger.debug(f"Importing {module}...")
                m = importlib.import_module(module)
            except Exception as e:
                main_logger.error(f"Failed to import module {module}: {e}")
                continue
            for index, sub_mod in enumerate(sub_mods):
                if "active" not in sub_mod:
                    main_logger.warning(
                        f"In toml_file {args.toml_file}, section {module}[{index}] has no entry active=true|false, skipping this module"
                    )
                    continue
                else:
                    if "name" not in sub_mod:
                        if single_instance is True:
                            toml_data[module]["name"] = module
                            sub_mod["name"] = module
                        else:
                            toml_data[module][index]["name"] = f"{module}.{index}"
                            sub_mod["name"] = f"{module}.{index}"
                        name = sub_mod["name"]
                        main_logger.info(f"Module {module} has no name, using {name}")
                    if sub_mod["active"] is True:

                        obj_name = sub_mod["name"]
                        ind = rfind(obj_name, '.')
                        if ind != -1:
                            obj_name = obj_name[:ind]
                        try:
                            ev_proc = m.EventProcessor(toml_data["indrajala"], sub_mod)
                        except Exception as e:
                            main_logger.error(
                                f"Failed to import EventProcessor from module {module}: {e}"
                            )
                            continue
                        try:
                            if ev_proc.isActive() is False:
                                main_logger.error(
                                    f"Failed to initialize module {module}"
                                )
                                continue
                        except Exception as e:
                            main_logger.error(
                                f"Failed to detect activity-state of module {module}: {e}"
                            )
                            continue
                        methods = ["get", "put"]
                        for method in methods:
                            m_op = getattr(ev_proc, method, None)
                            if callable(m_op) is False:
                                main_logger.error(
                                    f"Failed to import EventProcessor from module {module} has no {method} function"
                                )
                                continue
                        modules[sub_mod["name"]] = ev_proc
                        main_logger.info(f"Import {module} success.")
                    else:
                        main_logger.info(f"Module [{module}] is not active.")
    main_logger.info(f"Loaded modules: {modules}")
    return modules


def read_config_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config-dir",
        action="store",
        dest="config_dir",
        type=pathlib.Path,
        default="config",
        help="path to config_dir that contains indrajala.toml and other config files.",
    )
    parser.add_argument(
        "-k",
        action="store_true",
        dest="kill_daemon",
        help="Kill existing instance and terminate.",
    )

    args = parser.parse_args()

    config_dir = args.config_dir
    toml_file = os.path.join(config_dir, "indrajala.toml")

    try:
        with open(toml_file, "rb") as f:
            toml_data = tomllib.load(f)
    except Exception as e:
        print(f"Couldn't read {toml_file}, {e}")
        exit(0)
    if args.kill_daemon is True:
        toml_data["in_signal_server"]["kill_daemon"] = True
    else:
        toml_data["in_signal_server"]["kill_daemon"] = False
    toml_data["indrajala"]["config_dir"] = str(config_dir)

    loglevel_console = (
        toml_data["indrajala"].get("max_loglevel_console", "info").upper()
    )
    loglevel_file = toml_data["indrajala"].get("max_loglevel_logfile", "debug").upper()
    main_loglevel = toml_data["indrajala"].get("loglevel", "info").upper()
    llc = logging.getLevelName(loglevel_console)
    llf = logging.getLevelName(loglevel_file)

    # logging.basicConfig(level=logging.DEBUG)
    root_logger = logging.getLogger()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    # root_logger.setLevel(logging.DEBUG)

    msh = logging.StreamHandler()
    msh.setLevel(llc)
    msh.setFormatter(formatter)
    root_logger.addHandler(msh)

    log_dir = toml_data["indrajala"]["logdir"]
    if "{configdir}" in log_dir:
        log_dir = log_dir.replace("{configdir}", str(config_dir))
    log_file = os.path.join(log_dir, "indrajala.log")
    try:
        # mfh = logging.FileHandler(log_file, mode='w')
        mfh = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            backupCount=toml_data["indrajala"].get("log_rotate_days", 1),
        )
        mfh.setLevel(llf)
        mfh.setFormatter(formatter)
        root_logger.addHandler(mfh)
    except Exception as e:
        mfh = None
        print(f"FATAL: failed to create file-handler for logging at {log_file}: {e}")

    main_logger = logging.getLogger("IndraMain")
    main_logger.setLevel(main_loglevel)

    main_logger.info("----------------------------------------------------------")
    main_logger.info(f"   Starting Indrajala server {INDRAJALA_VERSION}")

    return main_logger, toml_data, args


main_logger, toml_data, args = read_config_arguments()
main_logger.info(f"indrajala: starting version {INDRAJALA_VERSION}")
modules = load_modules(main_logger, toml_data, args)

terminate_main_runner = False
try:
    main_runner(main_logger, modules)
except KeyboardInterrupt:
    terminate_main_runner = True
