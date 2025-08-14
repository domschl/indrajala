import sys
import subprocess
import json
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
ASD_PATH = os.path.abspath(os.path.join(ROOT_DIR, "cl_indrajala", "indralib", "indralib.asd"))
CL_TESTS_PATH = os.path.abspath(os.path.join(ROOT_DIR, "cl_indrajala", "indralib", "tests", "indra_tests.lisp"))
TEST_DATA_DIR = os.path.abspath(os.path.join(ROOT_DIR, "test_data"))
DOMAIN_DIR = os.path.join(TEST_DATA_DIR, "domain")
TIME_DIR = os.path.join(TEST_DATA_DIR, "time")
JS_MQCMP = os.path.abspath(os.path.join(ROOT_DIR, "js_indrajala", "indralib", "tests", "indra_mqcmp_tests.js"))
JS_TIME = os.path.abspath(os.path.join(ROOT_DIR, "js_indrajala", "indralib", "tests", "indra_time_tests.js"))
PY_MQCMP = os.path.abspath(os.path.join(ROOT_DIR, "indralib", "tests", "mq_cmp.py"))
PY_TIME = os.path.abspath(os.path.join(ROOT_DIR, "indralib", "tests", "time_tests.py"))
SWIFT_PKG = os.path.abspath(os.path.join(ROOT_DIR, "swift_indrajala", "indratest"))

test_tasks = [
    {
        "name": "js_indralib mqcmp domain tests via Node.js",
        "cmd": f"node {JS_MQCMP} --folder={DOMAIN_DIR}",
        "failure_sim_cmd": f"node {JS_MQCMP} --folder={DOMAIN_DIR} --include_failure_cases=true",
    },
    {
        "name": "py_indralib_indra_mqcmp_tests via Python",
        "cmd": f"python {PY_MQCMP} --folder={DOMAIN_DIR}",
        "failure_sim_cmd": f"python {PY_MQCMP} --folder={DOMAIN_DIR} --include_failure_cases=true",
    },
    {
        "name": "js_indralib time tests via Node.js",
        "cmd": f"node {JS_TIME} --folder={TIME_DIR}",
    },
    {
        "name": "py_indralib_indra_time_tests via Python",
        "cmd": f"python {PY_TIME} --folder={TIME_DIR}",
    },
    {
        "name": "swift_indralib domain tests via Swift",
        "cmd": f"swift run --package-path {SWIFT_PKG} indratest --folder={TEST_DATA_DIR} --include_failure_cases=false --test_cases=domain",
        "failure_sim_cmd": f"swift run --package-path {SWIFT_PKG} indratest --folder={TEST_DATA_DIR} --include_failure_cases=true --test_cases=domain",
    },
    {
        "name": "swift_indralib time tests via Swift",
        "cmd": f"swift run --package-path {SWIFT_PKG} indratest --folder={TEST_DATA_DIR} --include_failure_cases=false --test_cases=time",
    },
    {
        "name": "cl_indralib tests via SBCL",
        "cmd": f"sbcl --noinform --non-interactive --eval '(asdf:load-asd \"{ASD_PATH}\")' --eval '(ql:quickload :indralib)' --load \"{CL_TESTS_PATH}\" --eval '(indralib.tests:main \"--folder={TEST_DATA_DIR}\" \"--include_failure_cases=false\")'",
        "failure_sim_cmd": f"sbcl --noinform --non-interactive --eval '(asdf:load-asd \"{ASD_PATH}\")' --eval '(ql:quickload :indralib)' --load \"{CL_TESTS_PATH}\" --eval '(indralib.tests:main \"--folder={TEST_DATA_DIR}\" \"--include_failure_cases=true\")'",
    },
]


def run_process_and_capture_output(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    output, _ = process.communicate()

    token = "#$#$# Result #$#$#\n"
    start_index = output.decode("utf-8").find(token)
    if start_index != -1:
        start_index += len(token)
        json_str = output[start_index:].strip()
        json_obj = json.loads(json_str)
        return json_obj

    return None


def run_tests(test_tasks, simulate_failures=False):
    cumul = {
        "num_ok": 0,
        "num_failed": 0,
        "num_skipped": 0,
        "errors": [],
    }
    for task in test_tasks:
        if simulate_failures is True:
            if "failure_sim_cmd" not in task:
                print(f"Skipping test: {task['name']} as no failure cases are provided")
                continue
            print(f"Running test: {task['name']} with failure cases")
            result = run_process_and_capture_output(task["failure_sim_cmd"])
        else:
            print(f"Running test: {task['name']}")
            result = run_process_and_capture_output(task["cmd"])
        if result is not None:
            print(json.dumps(result, indent=2))
            cumul["num_ok"] += result["num_ok"]
            cumul["num_failed"] += result["num_failed"]
            cumul["num_skipped"] += result["num_skipped"]
            cumul["errors"].extend(result["errors"])
        else:
            print(f"FATAL: No result found for test: {task['name']}")
            exit(-1)
    print("----------------------------------------------")
    print("Cumulative results")
    print(json.dumps(cumul, indent=2))


if __name__ == "__main__":
    args = sys.argv[1:]
    simulate_failures = False
    for arg in args:
        if arg == "--fails":
            simulate_failures = True
    run_tests(test_tasks, simulate_failures=simulate_failures)
