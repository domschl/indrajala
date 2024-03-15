# Add the parent directory to the path so we can import the client
import sys
import os

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
print(path)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore
from indra_time import IndraTime  # type: ignore

# c.f. https://aa.usno.navy.mil/data/JulianDate,

# [xx]_table are from: https://github.com/sarabveer/calendrica-js/blob/master/test/

jd_table = [
    1507231.5,
    1660037.5,
    1746893.5,
    1770641.5,
    1892731.5,
    1931579.5,
    1974851.5,
    2091164.5,
    2121509.5,
    2155779.5,
    2174029.5,
    2191584.5,
    2195261.5,
    2229274.5,
    2245580.5,
    2266100.5,
    2288542.5,
    2290901.5,
    2323140.5,
    2334848.5,
    2348020.5,
    2366978.5,
    2385648.5,
    2392825.5,
    2416223.5,
    2425848.5,
    2430266.5,
    2430833.5,
    2431004.5,
    2448698.5,
    2450138.5,
    2465737.5,
    2486076.5,
]

rd_table = [
    -214193,
    -61387,
    25469,
    49217,
    171307,
    210155,
    253427,
    369740,
    400085,
    434355,
    452605,
    470160,
    473837,
    507850,
    524156,
    544676,
    567118,
    569477,
    601716,
    613424,
    626596,
    645554,
    664224,
    671401,
    694799,
    704424,
    708842,
    709409,
    709580,
    727274,
    728714,
    744313,
    764652,
]

gregorian_table = [
    {"year": -586, "month": 7, "day": 24},
    {"year": -168, "month": 12, "day": 5},
    {"year": 70, "month": 9, "day": 24},
    {"year": 135, "month": 10, "day": 2},
    {"year": 470, "month": 1, "day": 8},
    {"year": 576, "month": 5, "day": 20},
    {"year": 694, "month": 11, "day": 10},
    {"year": 1013, "month": 4, "day": 25},
    {"year": 1096, "month": 5, "day": 24},
    {"year": 1190, "month": 3, "day": 23},
    {"year": 1240, "month": 3, "day": 10},
    {"year": 1288, "month": 4, "day": 2},
    {"year": 1298, "month": 4, "day": 27},
    {"year": 1391, "month": 6, "day": 12},
    {"year": 1436, "month": 2, "day": 3},
    {"year": 1492, "month": 4, "day": 9},
    {"year": 1553, "month": 9, "day": 19},
    {"year": 1560, "month": 3, "day": 5},
    {"year": 1648, "month": 6, "day": 10},
    {"year": 1680, "month": 6, "day": 30},
    {"year": 1716, "month": 7, "day": 24},
    {"year": 1768, "month": 6, "day": 19},
    {"year": 1819, "month": 8, "day": 2},
    {"year": 1839, "month": 3, "day": 27},
    {"year": 1903, "month": 4, "day": 19},
    {"year": 1929, "month": 8, "day": 25},
    {"year": 1941, "month": 9, "day": 29},
    {"year": 1943, "month": 4, "day": 19},
    {"year": 1943, "month": 10, "day": 7},
    {"year": 1992, "month": 3, "day": 17},
    {"year": 1996, "month": 2, "day": 25},
    {"year": 2038, "month": 11, "day": 10},
    {"year": 2094, "month": 7, "day": 18},
]

julian_table = [
    {"year": -587, "month": 7, "day": 30},
    {"year": -169, "month": 12, "day": 8},
    {"year": 70, "month": 9, "day": 26},
    {"year": 135, "month": 10, "day": 3},
    {"year": 470, "month": 1, "day": 7},
    {"year": 576, "month": 5, "day": 18},
    {"year": 694, "month": 11, "day": 7},
    {"year": 1013, "month": 4, "day": 19},
    {"year": 1096, "month": 5, "day": 18},
    {"year": 1190, "month": 3, "day": 16},
    {"year": 1240, "month": 3, "day": 3},
    {"year": 1288, "month": 3, "day": 26},
    {"year": 1298, "month": 4, "day": 20},
    {"year": 1391, "month": 6, "day": 4},
    {"year": 1436, "month": 1, "day": 25},
    {"year": 1492, "month": 3, "day": 31},
    {"year": 1553, "month": 9, "day": 9},
    {"year": 1560, "month": 2, "day": 24},
    {"year": 1648, "month": 5, "day": 31},
    {"year": 1680, "month": 6, "day": 20},
    {"year": 1716, "month": 7, "day": 13},
    {"year": 1768, "month": 6, "day": 8},
    {"year": 1819, "month": 7, "day": 21},
    {"year": 1839, "month": 3, "day": 15},
    {"year": 1903, "month": 4, "day": 6},
    {"year": 1929, "month": 8, "day": 12},
    {"year": 1941, "month": 9, "day": 16},
    {"year": 1943, "month": 4, "day": 6},
    {"year": 1943, "month": 9, "day": 24},
    {"year": 1992, "month": 3, "day": 4},
    {"year": 1996, "month": 2, "day": 12},
    {"year": 2038, "month": 10, "day": 28},
    {"year": 2094, "month": 7, "day": 5},
]


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
    with open("source_data/date_data.md", "r") as f:
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
            year = -int(year)
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
    if (
        len(jd_table) != len(rd_table)
        or len(rd_table) != len(gregorian_table)
        or len(gregorian_table) != len(julian_table)
    ):
        raise ValueError("Table lengths do not match")
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


def cmp_time(d1: str, d2: str):
    l1 = len(d1)
    l2 = len(d2)
    if l1 < l2:
        d2 = d2[: len(d1)]
    if l2 < l1:
        d1 = d1[: len(d2)]
    return d1 == d2


data = (
    read_calendrical_test_data()
)  # Read markdown-table from 'Calendrical Calculations'
data = morph_calendrical_data(data)  # Convert to more useful format
data = add_js_data(
    data
)  # Add Test-Data from https://github.com/sarabveer/calendrica-js
# sort by 'RD':
data = sorted(data, key=lambda x: x["RD"])

errors = 0
for d in data:
    d["indra_text"] = IndraTime.julian2ISO(d["JulianDate"])
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
        errors += 1
    d["Result"] = res

for d in data:
    print(d)
print(f"Errors: {errors}")
