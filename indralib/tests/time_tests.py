# Add the parent directory to the path so we can import the client
import sys
import os
import json
import math

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


def do_tests(data, data2):
    result = {
                "num_ok": 0,
                "num_failed": 0,
                "num_skipped": 0,
                "errors": []
            };
    for d in data:
        d["indra_text"] = IndraTime.julian_to_ISO(d["JulianDate"])
        d["indra_jd"] = IndraTime.ISO_to_julian(d["indra_text"])
        d["indra_human"] = IndraTime.julian_to_string_time(d["JulianDate"])
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

    for d in data2:
        gr = d["Gregorian year"]
        bp = d["BP year"]
        jd1 = IndraTime.string_time_to_julian(gr)[0]
        jd2 = IndraTime.string_time_to_julian(bp)[0]
        bpf = int(bp.split(" ")[0])
        year = 1950 - bpf
        month = 1
        day = 1
        hour = 0
        minute = 0
        second = 0
        microsecond = 0
        jd3 = jdt = IndraTime.discrete_time_to_julian(
                    year, month, day, hour, minute, second, microsecond
                )
        if math.isclose(jd1, jd3, abs_tol=0.0001):
            result["num_ok"] += 1
        else:
            result["num_failed"] += 1
            err_msg = f"Error: {jd1} != {jd3} at test {d["Event"]}"
            result["errors"].append(err_msg)
    return result

# for d in data:
#     print(d)
# print(f"Errors: {errors}")
folder ="../../test_data/time"
for arg in sys.argv:
    if arg.startswith("--folder="):
        folder = arg.split("=")[1]

with open(os.path.join(folder, "normalized_jd_time_data.json")) as f:
    data1 = json.load(f)
with open(os.path.join(folder, "normalized_bp_time_data.json")) as f:
    data2 = json.load(f)

result = do_tests(data1, data2)

print("#$#$# Result #$#$#")
print(json.dumps(result, indent=2))
