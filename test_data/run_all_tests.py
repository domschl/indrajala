import subprocess
import json


test_tasks = [
    {
        "name": "js_indralib mqcmp domain tests via Node.js",
        "cmd": "node ../js_indrajala/indralib/tests/indra_tests.js --folder=domain",
        "failure_sim_cmd": "node ../js_indrajala/indralib/tests/indra_tests.js --folder=domain --include_failure_cases=true",
    },
    {
        "name": "py_indralib_indra_time_tests via Python",
        "cmd": "python ../indralib/tests/time_tests.py --folder=time",
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
        else:
            print(f"No result found for test: {task['name']}")


if __name__ == "__main__":
    run_tests(test_tasks, simulate_failures=False)
