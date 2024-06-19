# Add the parent directory to the path so we can import the client
import sys
import os
import json

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src/")
print(path)
sys.path.append(path)
from indralib.indra_event import IndraEvent  # type: ignore
from indralib.indra_time import IndraTime  # type: ignore


def do_tests(data):
    result = {"num_ok": 0, "num_failed": 0, "num_skipped": 0, "errors": []}
    for d in data:
        pub = d["publish"]
        sub = d["subscribe"]
        res = d["result"]
        if IndraEvent.mqcmp(pub, sub) == res:
            result["num_ok"] += 1
        else:
            result["num_failed"] += 1
            result["errors"].append(f"Error: {pub} {sub} != {res}")
    return result


folder = "../../test_data/domain"
do_failure_cases = False
for arg in sys.argv:
    if arg.startswith("--folder="):
        folder = arg.split("=")[1]
    if arg == "--include_failure_cases=true":
        do_failure_cases = True

if do_failure_cases is True:
    data_filename = "domain_failure_cases.json"
else:
    data_filename = "domain_publish_subscribe_data.json"

with open(os.path.join(folder, data_filename)) as f:
    data = json.load(f)
    result = do_tests(data)

    print("#$#$# Result #$#$#")
    print(json.dumps(result, indent=2))
