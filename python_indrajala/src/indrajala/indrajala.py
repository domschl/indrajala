import os
import logging
import argparse
import pathlib
import tomlkit
import asyncio
import importlib


indrajala_version = '0.0.1'


def mqcmp(pub, sub):
    for c in ['+', '#']:
        if pub.find(c) != -1:
            print(f"Illegal char '{c}' in pub in mqcmp!")
            return False
    inds = 0
    wcs = False
    for indp in range(len(pub)):
        if wcs is True:
            if pub[indp] == '/':
                inds += 1
                wcs = False
            continue
        if inds >= len(sub):
            return False
        if pub[indp] == sub[inds]:
            inds += 1
            continue
        if sub[inds] == '#':
            return True
        if sub[inds] == '+':
            wcs = True
            inds += 1
            continue
        if pub[indp] != sub[inds]:
            # print(f"{pub[indp:]} {sub[inds:]}")
            return False
    if len(sub[inds:]) == 0:
        return True
    if len(sub[inds:]) == 1:
        if sub[inds] == '+' or sub[inds] == '#':
            return True
    return False


async def main_runner(main_logger, modules, toml_data, args):
    loop = asyncio.get_running_loop()
    subs = {}

    for module in modules:
        main_logger.debug(f"async_init of {module}")
        subs[module] = await modules[module].async_init(loop)

    tasks = []
    for module in modules:
        m_op = getattr(modules[module], "server_task", None)
        if callable(m_op) is True:
            tasks.append(asyncio.create_task(modules[module].server_task()))
            main_logger.info(f"Task {module} has separate server_task(), started module-specific background server")
        main_logger.debug(f"adding task from {module}")
        tasks.append(asyncio.create_task(modules[module].get()))

    global terminate_main_runner
    terminate_main_runner = False

    active_tasks = tasks
    while terminate_main_runner is False:
        main_logger.debug(f"Active tasks1: {len(active_tasks)}")
        finished_tasks, active_tasks = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
        main_logger.debug(f"Active tasks2: {len(active_tasks)}")
        for task in finished_tasks:
            res = task.result()
            if res is None or 'topic' not in res or 'origin' not in res:
                main_logger.warning(f"Invalid empty msg {res}")
                continue
            main_logger.debug(f"Finished: {res}")
            origin_module = res['origin']
            main_logger.debug(f"adding task from {origin_module}")
            main_logger.info(f"Getting {origin_module}")
            if len(active_tasks) == 0:
                active_tasks = [asyncio.create_task(modules[origin_module].get())]
            else:
                active_tasks = active_tasks.union((asyncio.create_task(modules[origin_module].get()),))
            if 'cmd' not in res:
                main_logger.error(f"Invalid result without 'cmd' field: {res}")
                continue
            if res['cmd']=='event':
                if 'topic' in res and res['topic'] is not None:
                    for module in modules:
                        if module != origin_module:
                            for sub in subs[module]:
                                if mqcmp(res['topic'], sub) is True:
                                    await modules[module].put(res)
                                    break
            elif res['cmd']=='system':
                if 'topic' in res and res['topic'] is not None:
                    if res['topic'] == "$SYS/PROCESS":
                        if 'msg' in res and res['msg'] == 'QUIT':
                            terminate_main_runner = True
                            continue
            elif res['cmd']=='ping':
                main_logger.info(f"Received and ignored ping {res}")
            else:
                main_logger.error(f"Unknown cmd {res['cmd']} in {res}")
    main_logger.info("All done, terminating indrajala.")


def load_modules(main_logger, toml_data, args):
    modules = {}
    if 'indrajala' not in toml_data:
        main_logger.error(f'The toml_file {args.toml_file} needs to contain a section [indrajala], cannot continue with invalid configuration.')
        return {}
    if 'modules' not in toml_data['indrajala']:
        main_logger.warning(f'In toml_file {args.toml_file}, [indrajala] has no list of modules, add: modules=[..]')
        return {}
    for module in toml_data['indrajala']['modules']:
        if module not in toml_data:
            main_logger.warning(f'In toml_file {args.toml_file}, no configuration section [{module}] found, skipping this module')
        else:
            if 'active' not in toml_data[module]:
                main_logger.warning(f'In toml_file {args.toml_file}, section [{module}] has no entry active=true|false, skipping this module')
            else:
                if toml_data[module]['active'] is True:
                    main_logger.info(f'Activating module [{module}]')
                    try:
                        main_logger.debug(f"Importing {module}...")
                        m = importlib.import_module(module)
                    except Exception as e:
                        main_logger.error(f'Failed to import module {module}: {e}')
                        toml_data[module]['active'] = False
                        continue
                    try:
                        ev_proc = m.EventProcessor(module, main_logger, toml_data)
                    except Exception as e:
                        main_logger.error(f'Failed to import EventProcessor from module {module}: {e}')
                        continue
                    methods = ['get', 'put']
                    for method in methods:
                        m_op = getattr(ev_proc, method, None)
                        if callable(m_op) is False:
                            main_logger.error(f'Failed to import EventProcessor from module {module} has no {method} function')
                            continue
                    modules[module] = ev_proc
                    main_logger.debug(f"Import {module} success.")
                else:
                    main_logger.debug(f'Module [{module}] is not active.')
    return modules


def read_config_arguments():
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config-dir', action='store', dest="config_dir", type=pathlib.Path, default='config', help="path to config_dir that contains indrajala.toml and other config files.")
    parser.add_argument('-l', '--log-dir', action='store', dest="log_dir", type=pathlib.Path, default='log', help='filepath to log directory')
    parser.add_argument('-k', action='store_true', dest='kill_daemon', help='Kill existing instance and terminate.')

    args = parser.parse_args()

    main_logger = logging.getLogger('indrajala_core')
    main_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')

    msh = logging.StreamHandler()
    msh.setLevel(logging.DEBUG)
    msh.setFormatter(formatter)
    main_logger.addHandler(msh)

    log_file = os.path.join(args.log_dir, 'indrajala.log')
    mfh = logging.FileHandler(log_file, mode='w')
    mfh.setLevel(logging.DEBUG)
    mfh.setFormatter(formatter)
    main_logger.addHandler(mfh)

    config_dir = args.config_dir
    toml_file = os.path.join(config_dir, 'indrajala.toml')

    try:
        with open(toml_file, 'r') as f:
            toml_data = tomlkit.parse(f.read())
    except Exception as e:
        main_logger.warning(f"Couldn't read {toml_file}, {e}")
        exit(0)
    if args.kill_daemon is True:
        toml_data['in_signal_server']['kill_daemon'] = True
    else:
        toml_data['in_signal_server']['kill_daemon'] = False

    toml_data['indrajala']['config_dir'] = str(config_dir)
    return main_logger, toml_data, args


def test_mqcmp():
    td = [('abc', 'abc', True), ('ab', 'abc', False), ('ab', 'ab+', True),
          ('abcd/dfew', 'abcd', False), ('ba', 'bdc/ds', False), ('abc/def', 'abc/+', True),
          ('abc/def', 'asdf/+/asdf', False), ('abc/def/asdf', 'abc/+/asdf', True),
          ('abc/def/ghi', '+/+/+', True), ('abc/def/ghi', '+/+/', False), ('abc/def/ghi', '+/+/+/+', False),
          ('abc/def/ghi', '+/#', True), ('abc/def/ghi', '+/+/#', True), ('abc/def/ghi', '+/+/+/#', False)]
    for t in td:
        pub = t[0]
        sub = t[1]
        if mqcmp(pub, sub) != t[2]:
            print(f"pub:{pub}, sub:{sub} = {t[2]}!=ground truth")
            print("Fix your stuff first!")
            exit(-1)


test_mqcmp()
main_logger, toml_data, args = read_config_arguments()
main_logger.info(f"indrajala: starting version {indrajala_version}")
modules = load_modules(main_logger, toml_data, args)

terminate_main_runner = False
try:
    asyncio.run(main_runner(main_logger, modules, toml_data, args), debug=True)
except KeyboardInterrupt:
    terminate_main_runner = True
