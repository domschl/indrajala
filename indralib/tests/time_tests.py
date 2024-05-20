# Add the parent directory to the path so we can import the client
import sys
import os
import json

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src/")
print(path)
sys.path.append(path)
from indralib.indra_event import IndraEvent  # type: ignore
from indralib.indra_time import IndraTime  # type: ignore


def cmp_time(d1: str, d2: str):
    l1 = len(d1)
    l2 = len(d2)
    if l1 < l2:
        d2 = d2[: len(d1)]
    if l2 < l1:
        d1 = d1[: len(d2)]
    return d1 == d2


def do_tests(data):
    result = {
                "num_ok": 0,
                "num_failed": 0,
                "num_skipped": 0,
                "errors": []
            };
    for d in data:
        d["indra_text"] = IndraTime.julian2ISO(d["JulianDate"])
        d["indra_jd"] = IndraTime.ISO2julian(d["indra_text"])
        d["indra_human"] = IndraTime.julian_2_string_time(d["JulianDate"])
        res = ""
        it = d["indra_text"]
        if it.endswith(" BC"):
            it = "-" + it[:-3]

        if cmp_time(d["julian_string"], it):
            res += "[JD]"
        if cmp_time(d["gregorian_string"], it):
            res += "[GD]"
        if res == "":
            res = "Error"
            result["num_failed"] += 1
            err_msg = f"Error: Both {d['julian_string']} and {d['gregorian_string']} != {it}"
            result["errors"].append(err_msg)
        else:
            result["num_ok"] += 1

        if d["indra_jd"] != d["JulianDate"]:
            res += f"[JD-Error: {d["indra_jd"]} {d["JulianDate"]}]"
            err_msg = f"Error: {d["indra_jd"]} != {d["JulianDate"]}"
            result["errors"].append(err_msg)
            result["num_failed"] += 1
        else:
            result["num_ok"] += 1
    return result

# for d in data:
#     print(d)
# print(f"Errors: {errors}")
folder ="../../test_data/time"
for arg in sys.argv:
    if arg.startswith("--folder="):
        folder = arg.split("=")[1]

with open(os.path.join(folder, "normalized_jd_time_data.json")) as f:
    global data
    data = json.load(f)
    result = do_tests(data)

    print("#$#$# Result #$#$#")
    print(json.dumps(result, indent=2))
