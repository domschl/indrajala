# Add the parent directory to the path so we can import the client
import sys
import os
import json

# c.f. https://aa.usno.navy.mil/data/JulianDate,
# c.f. https://ssd.jpl.nasa.gov/tools/jdc/#/cd
# [xx]_table are from: https://github.com/sarabveer/calendrica-js/blob/master/test/

# import tabes from time/raw/time_tables.py
sys.path.append(os.path.join(os.path.dirname(__file__), "time", "raw"))
from time_tables import calendrica_js_tables


def markdown_table_to_dict(markdown_text):
    # Check, if markdown_text is array of lines:
    if isinstance(markdown_text, list) is False:
        data = markdown_text.split("\n")
    else:
        data = markdown_text
    data = [x.split("|") for x in data if len(x) > 0 and x[0] == "|"]
    data = [x for x in data if len(x) > 1]
    headers = [x.strip() for x in data[0] if len(x.strip()) > 0]
    data = data[2:]
    data = [
        dict(zip(headers, [y.strip() for y in x if len(y.strip()) > 0])) for x in data
    ]
    print("---")
    print(data)
    print("---")
    return data


def extract_markdown_tables(markdown_text):
    data = markdown_text.split("\n")
    tables = []
    table_data = []
    for line in data:
        if line.startswith("|"):
            table_data.append(line)
        else:
            if len(table_data) > 0:
                tables.append(markdown_table_to_dict(table_data))
                table_data = []
    if len(table_data) > 0:
        tables.append(markdown_table_to_dict(table_data))
    return tables


def read_calendrical_test_data():
    with open("time/raw/date_data.md", "r") as f:
        markdown_text = f.read()
    tables = extract_markdown_tables(markdown_text)
    return tables[0]


def read_bp_test_data():
    with open("time/raw/time_bp.md", "r") as f:
        markdown_text = f.read()
    tables = extract_markdown_tables(markdown_text)
    return tables[0]


def morph_calendrical_data(data):
    out_data = []
    for d in data:
        d_new = {}
        d_new["Calendar"] = d["Calendar"]
        d_new["RD"] = float(d["Epoch (R.D.)"])
        d_new["JulianDate"] = float(d["Epoch (R.D.)"]) + 1721424.5
        jul_string = d["Equivalent Julian"].replace(" (Julian)", "")
        greg_string = d["Equivalent Gregorian"].replace(" (Gregorian)", "")
        # Convert "July 16, 622 B.C.E or A.D. to signed -622-07-16 (for all month names)"
        month_names = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        parts = [x.replace(",", "") for x in jul_string.split(" ")]
        if parts[0] == "Noon":
            parts = parts[1:]
            hour = 12
        else:
            hour = 0
        year = int(parts[2])
        month = month_names.index(parts[0]) + 1
        day = int(parts[1])
        if parts[3] == "B.C.E.":
            year = -int(year) + 1
        jul_string = f"{year}-{month:02d}-{day:02d}T{hour:02d}:00:00"

        parts = [x.replace(",", "") for x in greg_string.split(" ")]
        if parts[0] == "Noon":
            parts = parts[1:]
            hour = 12
        else:
            hour = 0
        year = int(parts[2])
        month = month_names.index(parts[0]) + 1
        day = int(parts[1])
        greg_string = f"{year}-{month:02d}-{day:02d}T{hour:02d}:00:00"
        d_new["julian_string"] = jul_string
        d_new["gregorian_string"] = greg_string
        out_data.append(d_new)
    return out_data


def add_js_data(data=[]):
    jd_table = calendrica_js_tables["jd_table"]
    rd_table = calendrica_js_tables["rd_table"]
    gregorian_table = calendrica_js_tables["gregorian_table"]
    julian_table = calendrica_js_tables["julian_table"]
    if (
        len(jd_table) != len(rd_table)
        or len(rd_table) != len(gregorian_table)
        or len(gregorian_table) != len(julian_table)
    ):
        raise ValueError("Table lengths do not match in calendrica_js_tables.")
    for i in range(len(jd_table)):
        d = {
            "Calendar": "JS-Data",
            "RD": rd_table[i],
            "JulianDate": jd_table[i],
            "julian_string": f"{julian_table[i]['year']}-{julian_table[i]['month']:02d}-{julian_table[i]['day']:02d}T00:00:00",
            "gregorian_string": f"{gregorian_table[i]['year']}-{gregorian_table[i]['month']:02d}-{gregorian_table[i]['day']:02d}T00:00:00",
        }
        data.append(d)
    return data


def write_normalized_data(destination_file1, destination_file2):
    data = (
        read_calendrical_test_data()
    )  # Read markdown-table from 'Calendrical Calculations'
    data = morph_calendrical_data(data)  # Convert to more useful format
    data = add_js_data(
        data
    )  # Add Test-Data from https://github.com/sarabveer/calendrica-js
    # sort by 'RD':
    data = sorted(data, key=lambda x: x["RD"])
    with open(destination_file1, "wb") as f:
        f.write(json.dumps(data, indent=2).encode("utf-8"))

    data = read_bp_test_data()
    with open(destination_file2, "wb") as f:
        f.write(json.dumps(data, indent=2).encode("utf-8"))

    return data


if __name__ == "__main__":
    write_normalized_data(
        "time/normalized_jd_time_data.json", "time/normalized_bp_time_data.json"
    )
