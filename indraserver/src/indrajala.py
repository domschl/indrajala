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
import subprocess
import threading
import json
import time
import signal
import zmq
import shlex
import sys

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 and older:
    import tomli as tomllib  # type: ignore

from indralib.indra_event import IndraEvent

INDRAJALA_VERSION = "0.1.0"


def main_runner(main_logger, event_queue, modules):
    global abort_zmq_thread
    subs = {}

    for module in modules:
        default_subs = ["$cmd/quit", f"{module}/#"]
        subs[module] = []
        for sub in default_subs:
            if sub not in subs[module]:
                subs[module].append(sub)

    for module in modules:
        if modules[module]["mode"] == "queue":
            m_op = getattr(modules[module]["iproc"], "launcher", None)
            if callable(m_op) is True:
                main_logger.debug(f"adding task from {module}")
                p = mp.Process(target=modules[module]["iproc"].launcher, args=[])
                p.start()
                modules[module]["process"] = p
                main_logger.debug(f"Module {module} started")
            else:
                main_logger.error(
                    f"Cannot start process for {module}, entry-point 'indra_process' not found!"
                )

    # Main event loop
    terminate_main_runner = False
    stop_timer = None
    last_msg = time.time()
    dt_mean = 0
    stat_timer = time.time()
    high_water = 10
    unprocessed_items = 0
    last_stat_output = time.time()
    overview_mode = False
    qsize_implemented = True
    sysstat_subs = False
    while terminate_main_runner is False:
        if time.time() - stat_timer > 1.0:
            if qsize_implemented:
                try:
                    unprocessed_items = event_queue.qsize()
                except Exception as e:
                    main_logger.error(
                        "Your current platform doesn't support `qsize()` for multiprocessing queues, perf statistics will be invalid!"
                    )
                    qsize_implemented = False
            else:
                unprocessed_items = 0
            if unprocessed_items > high_water:
                main_logger.warning(
                    f"Main event loop overloaded: queue entries: {unprocessed_items}/{high_water}"
                )
            for module in modules:
                if qsize_implemented is True:
                    qs = modules[module]["send_queue"].qsize()
                else:
                    qs = 0
                unprocessed_items = unprocessed_items + qs
                if qs > high_water:
                    main_logger.warning(
                        f"Module {module} overloaded: queue entries: {qs}/{high_water}"
                    )
            stat_timer = time.time()
        ev = None
        while stop_timer is not None and event_queue.empty():
            if time.time() > stop_timer:
                terminate_main_runner = True
                break
            time.sleep(0.1)
        if terminate_main_runner is True:
            break
        ev = event_queue.get()
        # main_logger.info(f"Got event: {ev.to_json()}")

        origin_module = ev.from_id
        if "/" in origin_module:
            origin_module = origin_module.split("/")[0]
        if ev.domain.startswith("$log"):
            lvl = ev.domain.split("/")[-1]
            msg = f"{ev.from_id} - {ev.data}"
            if lvl == "error":
                main_logger.error(msg)
            elif lvl == "warning":
                main_logger.warning(msg)
            elif lvl == "info":
                main_logger.info(msg)
            elif lvl == "debug":
                main_logger.debug(msg)
        elif ev.domain.startswith("$cmd"):
            if ev.domain == "$cmd/quit":
                stop_timer = time.time() + 0.5
                for module in modules:
                    if modules[module]["mode"] == "queue":
                        main_logger.debug(
                            f"Sending termination cmd to {modules[module]['config_data']['name']}... "
                        )
                        modules[module]["send_queue"].put(ev)
                    elif modules[module]["mode"] == "zeromq":
                        main_logger.debug(
                            f"Sending termination cmd to {modules[module]['config_data']['name']} via zeromq... "
                        )
                        modules[module]["push_socket"].send_string(ev.to_json())
                    else:
                        main_logger.error(
                            f"Module {module} has no valid mode {modules[module]['mode']}, cannot send termination cmd"
                        )
            elif ev.domain == "$cmd/subs":
                sub_list = json.loads(ev.data)
                if isinstance(sub_list, list) is True:
                    for sub in sub_list:
                        if sub is not None:
                            if sub.startswith("$sys/stat"):
                                sysstat_subs = True
                            # if sub not in subs[origin_module]:  # XXX different sessions can sub to the same thing, alternative would be reference counting...
                            subs[origin_module].append(sub)
                            main_logger.info(f"Subscribing to {sub} by {origin_module}")
                        else:
                            main_logger.error(
                                f"Invalid subscription {sub} requested by {origin_module}"
                            )
            elif ev.domain == "$cmd/unsubs":
                sub_list = json.loads(ev.data)
                if isinstance(sub_list, list) is True:
                    for sub in sub_list:
                        if sub is not None:
                            if sub in subs[origin_module]:
                                subs[origin_module].remove(sub)
                                main_logger.debug(
                                    f"Unsubscribing from {sub} by {origin_module}"
                                )
                            if sub.startswith("$sys/stat"):
                                sysstat_subs = False
                                # Check if subscriber to sysstat is still active
                                for module in subs:
                                    for sub in subs[module]:
                                        if sub.startswith("$sys/stat"):
                                            sysstat_subs = True
                        else:
                            main_logger.error(
                                f"Invalid unsubscription {sub} requested by {origin_module}"
                            )
            else:
                main_logger.error(
                    f"Unknown command {ev.domain} received from {ev.from_id}, ignored."
                )
        else:
            mod_found = False
            route_target = False
            for module in modules:
                if module == origin_module:
                    mod_found = True
                if module != origin_module or True:
                    for sub in subs[module]:
                        if IndraEvent.mqcmp(ev.domain, sub) is True:
                            dt = time.time() - last_msg
                            if dt_mean == 0:
                                dt_mean = dt
                            avger = 100.0
                            dt_mean = ((avger - 1.0) * dt_mean + dt) / avger
                            if dt_mean > 0.0:
                                msg_sec = 1.0 / dt_mean
                            else:
                                msg_sec = 0.0
                            last_msg = time.time()
                            if msg_sec < 10.0:
                                if overview_mode is True:
                                    main_logger.info(
                                        "Switching back to single-message ROUTE infos, due to reduced message volume"
                                    )
                                    overview_mode = False
                                if time.time() - last_stat_output > 1.0:
                                    if sysstat_subs is True:
                                        # Only send statistics, if there is a subscriber
                                        ev_stat = IndraEvent()
                                        ev_stat.domain = "$sys/stat/msgpersec"
                                        ev_stat.data_type = "Float"
                                        ev_stat.from_id = "indrajala"
                                        ev_stat.data = json.dumps(msg_sec)
                                        # main_logger.info(f"JD-Time: {ev.time_jd_start}")
                                        event_queue.put(ev_stat)
                                    last_stat_output = time.time()
                                main_logger.info(
                                    f"ROUTE {ev.domain[:30]}={ev.data[:10]} to {module}, {msg_sec:0.2f} msg/s, que: {unprocessed_items}"
                                )
                            else:
                                if overview_mode is False:
                                    overview_mode = True
                                    main_logger.info(
                                        "Switching to ROUTE summary mode for routing, message volume > 10msg/sec"
                                    )
                                # main_logger.info(
                                #     f"ROUTE {ev.domain[:30]}={ev.data[:10]} to {module}, {msg_sec:0.2f} msg/s, que: {unprocessed_items}"
                                # )
                                if time.time() - last_stat_output > 1.0:
                                    main_logger.info(
                                        f"ROUTE summary {msg_sec:0.2f} msg/sec, queued: {unprocessed_items}"
                                    )
                                    if sysstat_subs is True:
                                        # Only send statistics, if there is a subscriber
                                        ev_stat = IndraEvent()
                                        ev_stat.domain = "$sys/stat/msgpersec"
                                        ev_stat.data_type = "Float"
                                        ev_stat.from_id = "indrajala"
                                        ev_stat.data = json.dumps(msg_sec)
                                        event_queue.put(ev_stat)
                                    last_stat_output = time.time()
                            if modules[module]["mode"] == "queue":
                                modules[module]["send_queue"].put(ev)
                            elif modules[module]["mode"] == "zeromq":
                                if modules[module]["push_socket"] is not None:
                                    modules[module]["push_socket"].send_json(
                                        ev.to_dict()
                                    )
                                else:
                                    main_logger.error(
                                        f"ZMQ socket for {module} not available, cannot send event {ev.domain}"
                                    )
                            else:
                                main_logger.error(
                                    f"Module {module} has no valid mode {modules[module]['mode']}, cannot route event {ev.domain}"
                                )
                            route_target = True
                            break
                else:
                    mod_found = True
            if mod_found is False and ev.from_id != "indrajala":
                main_logger.error(
                    f"Task {origin_module} not found, {origin_module} did not set from_id correctly"
                )
            if route_target is False:
                main_logger.warning(
                    f"No target found for {ev.domain}, {ev.data}, {ev.from_id}"
                )

    main_logger.debug("Waiting for all sub processes to terminate")
    if zmq_started is True:
        abort_zmq_thread = True
        main_logger.info("Informing ZMQ thread to terminate")
    # Wait for all processes to stop
    zmq_skip = False
    for module in modules:
        if modules[module]["mode"] == "queue":
            main_logger.debug(
                f"Waiting for termination of {modules[module]['config_data']['name']}... "
            )
            modules[module]["process"].join()
            main_logger.debug(f"{modules[module]['config_data']['name']} OK.")
        elif modules[module]["mode"] == "zeromq":
            reps = 5
            if modules[module]["push_socket"] is not None:
                modules[module]["push_socket"].close()
                modules[module]["push_socket"] = None
            modules[module]["iproc"].terminate()
            while modules[module]["iproc"].poll() is None:
                main_logger.info("Waiting for ZMQ process to terminate")
                if reps == 3:
                    modules[module]["iproc"].kill()
                    main_logger.warning(
                        "ZMQ process did not terminate, killing it with SIGKILL"
                    )
                time.sleep(0.5)
                reps = reps - 1
                if reps == 0:
                    zmq_skip = True
                    break
        else:
            main_logger.error(
                f"Module {module} has no valid mode {modules[module]['mode']}, cannot terminate it"
            )
    if zmq_skip is False:
        main_logger.info("All sub processes terminated")
    else:
        main_logger.warning(
            "Some sub processes were not terminated, ZMQ termination not yet implemented"
        )
    sys.exit(0)


def _handle_zmq_messages(socket):
    global abort_zmq_thread, event_queue
    main_logger.info("ZMQ thread started")
    while True:
        try:
            msg = socket.recv()
        except zmq.error.Again:
            if socket.closed or abort_zmq_thread is True:
                main_logger.info("ZMQ thread terminated")
                socket.close()
                return
            continue
        # main_logger.info(f"ZMQ message received: {msg}")
        ev = IndraEvent.from_json(msg)
        event_queue.put(ev)


def _create_zmq(zmq_port):
    global abort_zmq_thread, zmq_started, zmq_context
    if zmq_port < 1024 or zmq_port > 65535:
        main_logger.warning(f"Incorrect ZMQ port {zmq_port}, not starting ZMQ")
        return None
    else:
        abort_zmq_thread = False
        zmq_context = zmq.Context()
        socket = zmq_context.socket(zmq.PULL)
        socket.setsockopt(zmq.RCVTIMEO, 200)
        socket.bind(f"tcp://*:{zmq_port}")
        zmq_thread = threading.Thread(target=_handle_zmq_messages, args=(socket,))
        zmq_thread.start()
        logging.info(f"ZMQ thread started, listening on port {zmq_port}")
        zmq_started = True
        return socket


def load_modules(main_logger, toml_data, args):
    global zmq_started, zmq_context, event_queue
    modules = {}
    event_queue = mp.Queue()
    if "indrajala" not in toml_data:
        main_logger.error(
            f"The toml_file {args.toml_file} needs to contain a section [indrajala], cannot continue with invalid configuration."
        )
        return {}
    if "zeromq_port" not in toml_data["indrajala"]:
        main_logger.error(
            f"In toml_file {args.toml_file}, [indrajala] has no entry zeromq_port, cannot continue with invalid configuration."
        )
        return {}

    zmq_event_queue_port = toml_data["indrajala"]["zeromq_port"]
    zmq_started = False
    if zmq_event_queue_port is not None and zmq_event_queue_port != 0:
        main_logger.info(f"ZMQ active, listening on port {zmq_event_queue_port}")
        _create_zmq(zmq_event_queue_port)
    else:
        zmq_event_queue_port = 0

    if "modules" not in toml_data["indrajala"]:
        main_logger.error(
            f"In toml_file {args.toml_file}, [indrajala] has no list of modules, add: modules=[..]"
        )
        return {}
    for module in toml_data["indrajala"]["modules"]:
        if module not in toml_data:
            main_logger.warning(
                f"In toml_file, no configuration section [{module}] found, skipping this module"
            )
        else:
            sub_mods = []
            single_instance = True
            if isinstance(toml_data[module], list) is True:
                sub_mods = toml_data[module]
                single_instance = False
            else:
                sub_mods = [toml_data[module]]
            main_logger.debug(f"Activating module [{module}]")
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
                        main_logger.debug(f"Module {module} has no name, using {name}")
                    if sub_mod["active"] is True:
                        if "zeromq_port" not in sub_mod:
                            obj_name = sub_mod["name"]
                            ind = obj_name.rfind(".")
                            if ind != -1:
                                obj_name = obj_name[:ind]
                            modules[sub_mod["name"]] = {}
                            send_queue = mp.Queue()
                            modules[sub_mod["name"]]["mode"] = "queue"
                            modules[sub_mod["name"]]["send_queue"] = send_queue
                            modules[sub_mod["name"]]["config_data"] = sub_mod
                            modules[sub_mod["name"]]["iproc"] = m.IndraProcess(
                                sub_mod,
                                "queue",
                                event_queue,
                                send_queue,
                                zmq_event_queue_port,
                                0,
                            )
                            main_logger.debug(
                                f"Instantiation of {sub_mod['name']} success."
                            )
                        else:
                            if zmq_event_queue_port == 0:
                                main_logger.error(
                                    f"Module {sub_mod['name']} has a zeromq_port, but the main process is not listening on a ZMQ port, cannot start module."
                                )
                                continue
                            if "zeromq_executable" in sub_mod:
                                if not os.path.exists(sub_mod["zeromq_executable"]):
                                    main_logger.error(
                                        f"Module {sub_mod['name']} has a zeromq_port, but the executable {sub_mod['zeromq_executable']} does not exist, cannot start module."
                                    )
                                    continue
                                else:
                                    module = sub_mod["zmq_executable"]
                                    cmd = [
                                        module,
                                        str(zmq_event_queue_port),
                                        json.dumps(sub_mod),
                                    ]
                            else:
                                json_str = json.dumps(sub_mod)
                                escaped_json_str = shlex.quote(json_str)
                                module = f"indraserver/src/{sub_mod['name'].split('.')[0]}.py"
                                cmd = [
                                    "python",
                                    module,
                                    str(zmq_event_queue_port),
                                    escaped_json_str,
                                ]
                            # spawn a new process for the module
                            main_logger.debug(
                                f"Module {sub_mod['name']} has a zeromq_port, starting in separate process: {cmd}"
                            )
                            if "zeromq_host" in sub_mod:
                                host = sub_mod["zeromq_host"]
                            else:
                                host = "localhost"
                            modules[sub_mod["name"]] = {}
                            modules[sub_mod["name"]]["mode"] = "zeromq"
                            modules[sub_mod["name"]]["push_socket"] = None
                            modules[sub_mod["name"]]["send_port"] = sub_mod[
                                "zeromq_port"
                            ]
                            modules[sub_mod["name"]]["config_data"] = sub_mod
                            # Throws FileNotFoundError if the module is not found:
                            try:
                                modules[sub_mod["name"]]["iproc"] = subprocess.Popen(
                                    cmd
                                )
                            except FileNotFoundError as e:
                                main_logger.error(
                                    f"Module {sub_mod['name']} not found: {e}"
                                )
                                modules[sub_mod["name"]]["iproc"] = None
                                modules[sub_mod["name"]]["push_socket"].close()
                                modules[sub_mod["name"]]["push_socket"] = None
                                modules[sub_mod["name"]]["active"] = False
                                continue
                            socket = zmq_context.socket(zmq.PUSH)
                            modules[sub_mod["name"]][
                                "push_socket_uri"
                            ] = f"tcp://{host}:{sub_mod['zeromq_port']}"
                            main_logger.info(
                                f"Connecting to {sub_mod['name']} at {modules[sub_mod['name']]['push_socket_uri']}"
                            )
                            socket.connect(modules[sub_mod["name"]]["push_socket_uri"])
                            modules[sub_mod["name"]]["push_socket"] = socket
                            if socket is None:
                                main_logger.error(
                                    f"Module {sub_mod['name']} failed to connect to {modules[sub_mod['name']]['push_socket_uri']}"
                                )
                                modules[sub_mod["name"]]["active"] = False
                                continue
                    else:
                        main_logger.debug(
                            f"Module instance {sub_mod['name']} is not active."
                        )
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
    args = parser.parse_args()

    config_dir = args.config_dir
    toml_file = os.path.join(config_dir, "indrajala.toml")

    try:
        with open(toml_file, "rb") as f:
            toml_data = tomllib.load(f)
    except Exception as e:
        print(f"Couldn't read {toml_file}, {e}")
        exit(0)

    try:
        data_directory = os.path.expanduser(toml_data["indrajala"]["data_directory"])
    except Exception as _:
        data_directory = str(config_dir)

    try:
        with open(toml_file, "r") as f:
            cfg = f.read()
        cfg = cfg.replace("{{data_directory}}", data_directory)
        toml_data = tomllib.loads(cfg)
    except Exception as e:
        print(f"Replace wildcards and re-read of {toml_file} failed: {e}")
        exit(0)

    toml_data["indrajala"]["config_directory"] = str(config_dir)

    loglevel_console = (
        toml_data["indrajala"].get("max_loglevel_console", "debug").upper()
    )
    loglevel_file = toml_data["indrajala"].get("max_loglevel_logfile", "debug").upper()
    main_loglevel = toml_data["indrajala"].get("loglevel", "debug").upper()
    llm = logging.getLevelName(main_loglevel)
    llc = logging.getLevelName(loglevel_console)
    llf = logging.getLevelName(loglevel_file)

    # logging.basicConfig(level=llm)
    root_logger = logging.getLogger()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    root_logger.setLevel(llm)

    msh = logging.StreamHandler()
    msh.setLevel(llc)
    msh.setFormatter(formatter)
    root_logger.addHandler(msh)

    created_log_dir = False
    log_dir = toml_data["indrajala"]["logdir"]
    if "{configdir}" in log_dir:
        log_dir = log_dir.replace("{configdir}", str(config_dir))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        created_log_dir = True
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

    if created_log_dir:
        main_logger.info(f"   Created log directory {log_dir}")
    return main_logger, toml_data, args


def signal_handler(sig, frame):
    # print("MAIN_SIGNAL_HANDLER")
    main_logger.info("- - - - Termination sequence started - - - - - - -")
    ev = IndraEvent()
    ev.domain = "$cmd/quit"
    event_queue.put(ev)


def close_daemon():
    pass


if __name__ == "__main__":
    mp.set_start_method("spawn")
    main_logger, toml_data, args = read_config_arguments()
    main_logger.debug(f"indrajala: starting version {INDRAJALA_VERSION}")
    event_queue, modules = load_modules(main_logger, toml_data, args)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        main_runner(main_logger, event_queue, modules)
    except KeyboardInterrupt:
        print("KEYBOARD-INTERRUPT")
        pass
