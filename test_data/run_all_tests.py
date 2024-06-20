import sys
import subprocess
import json


test_tasks = [
    {
        "name": "js_indralib mqcmp domain tests via Node.js",
        "cmd": "node ../js_indrajala/indralib/tests/indra_mqcmp_tests.js --folder=domain",
        "failure_sim_cmd": "node ../js_indrajala/indralib/tests/indra_mqcmp_tests.js --folder=domain --include_failure_cases=true",
    },
    {
        "name": "py_indralib_indra_mqcmp_tests via Python",
        "cmd": "python ../indralib/tests/mq_cmp.py --folder=domain",
        "failure_sim_cmd": "python ../indralib/tests/mq_cmp.py --folder=domain --include_failure_cases=true",
    },
    {
        "name": "js_indralib time tests via Node.js",
        "cmd": "node ../js_indrajala/indralib/tests/indra_time_tests.js --folder=time",
    },
    {
        "name": "py_indralib_indra_time_tests via Python",
        "cmd": "python ../indralib/tests/time_tests.py --folder=time",
    },
    {
        "name": "swift_indralib domain tests via Swift",
        "cmd": "swift run --package-path ../swift_indrajala/indratest indratest --folder=../test_data --include_failure_cases=false --test_cases=domain",
        "failure_sim_cmd": "swift run --package-path ../swift_indrajala/indratest indratest --folder=../test_data --include_failure_cases=true --test_cases=domain",
    },
    {
        "name": "swift_indralib time tests via Swift",
        "cmd": "swift run --package-path ../swift_indrajala/indratest indratest --folder=../test_data --include_failure_cases=false --test_cases=time",
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
