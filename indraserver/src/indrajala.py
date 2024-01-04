"""
Main indrajala process
"""

import os
import logging
from logging.handlers import TimedRotatingFileHandler
import argparse
import pathlib
import importlib
import multiprocessing as mp
import json
import time
import signal

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 and older:
    import tomli as tomllib  # type: ignore

# XXX dev only
import sys
path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "indralib/src"
)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore

INDRAJALA_VERSION = "0.1.0"

        
def main_runner(main_logger, event_queue, modules):
    subs = {}

    for module in modules:
        default_subs = ["$cmd/quit", f"{module}/#"]
        subs[module]=[]
        for sub in default_subs:
            if sub not in subs[module]:
                subs[module].append(sub)

    for module in modules:
        m_op = getattr(modules[module]["iproc"], "launcher", None)
        if callable(m_op) is True:
            main_logger.debug(f"adding task from {module}")
            p = mp.Process(target=modules[module]["iproc"].launcher, args=[])
            p.start()
            modules[module]["process"] = p
            main_logger.info(f"Module {module} started")
        else:
            main_logger.error(f"Cannot start process for {module}, entry-point 'indra_process' not found!")

    # Main event loop
    terminate_main_runner = False
    stop_timer = None
    while terminate_main_runner is False:
        ev=None
        while stop_timer is not None and event_queue.empty():
            if time.time() > stop_timer:
                terminate_main_runner = True
                break
            time.sleep(0.1)
        if terminate_main_runner is True:
            break
        ev=event_queue.get()

        origin_module = ev.from_id
        if "/" in origin_module:
            origin_module = origin_module.split("/")[0]

        if ev.domain.startswith("$log"):
            lvl=ev.domain.split("/")[-1];
            msg=f"{ev.from_id} - {ev.data}"
            if lvl=="error":
                main_logger.error(msg)
            elif lvl=="warning":
                main_logger.warning(msg)
            elif lvl=="info":
                main_logger.info(msg)
            elif lvl=="debug":
                main_logger.debug(msg)
        elif ev.domain.startswith("$cmd"):
            if ev.domain == "$cmd/quit":
                stop_timer = time.time() + 0.5
                for module in modules:
                    main_logger.info(f"Sending termination cmd to {modules[module]['config_data']['name']}... ")
                    modules[module]["send_queue"].put(ev)
            elif ev.domain == "$cmd/subs":
                sub_list = json.loads(ev.data)
                if isinstance(sub_list, list) is True:
                    for sub in sub_list:
                        # if sub not in subs[origin_module]:  # XXX different sessions can sub to the same thing, alternative would be reference counting...
                        subs[origin_module].append(sub)
                        main_logger.info(f"Subscribing to {sub}")
            elif ev.domain == "$cmd/unsub":
                sub_list = json.loads(ev.data)
                if isinstance(sub_list, list) is True:
                    for sub in sub_list:
                        if sub in subs[origin_module]:
                            subs[origin_module].remove(sub)
                            main_logger.info(f"Unsubscribing from {sub}")

            else:
                main_logger.error(f"Unknown command {ev.domain} received from {ev.from_id}, ignored.")
        else:
            mod_found = False
            for module in modules:
                if module != origin_module:
                    for sub in subs[module]:
                        if IndraEvent.mqcmp(ev.domain, sub) is True:
                            main_logger.info(f"ROUTE {ev.domain} to {module}")
                            modules[module]["send_queue"].put(ev)
                else:
                    mod_found = True
            if mod_found is False:
                main_logger.error(
                    f"Task {origin_module} not found, {origin_module} did not set from_id correctly"
                )

    main_logger.info("Waiting for all sub processes to terminate")
    # Wait for all processes to stop
    for module in modules:
        main_logger.info(f"Waiting for termination of {modules[module]['config_data']['name']}... ")
        modules[module]['process'].join()
        main_logger.info(f"{modules[module]['config_data']['name']} OK.")
    main_logger.info("All sub processes terminated")
    exit(0)

def load_modules(main_logger, toml_data, args):
    modules = {}
    event_queue = mp.Queue()
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
                        ind = obj_name.rfind('.')
                        if ind != -1:
                            obj_name = obj_name[:ind]
                        modules[sub_mod["name"]] = {}
                        send_queue = mp.Queue()
                        modules[sub_mod["name"]]["send_queue"]=send_queue
                        modules[sub_mod["name"]]["config_data"]=sub_mod
                        modules[sub_mod["name"]]["iproc"]=m.IndraProcess(event_queue, send_queue, sub_mod) 
                        main_logger.info(f"Instantiation of {module} success.")
                    else:
                        main_logger.info(f"Module [{module}] is not active.")
    return (event_queue, modules)


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
        toml_data["signal_server"]["kill_daemon"] = True
    else:
        toml_data["signal_server"]["kill_daemon"] = False
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

def signal_handler(sig, frame):
    # print("MAIN_SIGNAL_HANDLER")
    main_logger.info("- - - - Termination sequence started - - - - - - -")
    ev = IndraEvent()
    ev.domain = "$cmd/quit"
    event_queue.put(ev)

def close_daemon():
    pass

if __name__ == '__main__':
    mp.set_start_method('spawn')
    main_logger, toml_data, args = read_config_arguments()
    main_logger.info(f"indrajala: starting version {INDRAJALA_VERSION}")
    event_queue, modules = load_modules(main_logger, toml_data, args)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        main_runner(main_logger, event_queue, modules)
    except KeyboardInterrupt:
        print("KEYBOARD-INTERRUPT")
        pass
