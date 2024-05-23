"use strict";
// Indralib shared ES6 module

import { IndraTime } from "../scripts/indra_time.js";
import { IndraEvent } from "../scripts/indralib.js";
import fs from 'fs';

const default_folder = "../../../test_data/time"
function load_test_Data(testDataFolder = default_folder) {
    const filePath = testDataFolder + "/normalized_jd_time_data.json";
    const fileContent = fs.readFileSync(filePath, 'utf-8');
    const jsonData = JSON.parse(fileContent);
    console.log(jsonData);
    return jsonData;
}



export class IndraTests {
    init_tests(folder = default_folder) {
        this.tests = load_test_Data(folder);
        this.errors = [];
        this.num_ok = 0;
        this.num_failed = 0;
        this.num_skipped = 0;
    }

    cmp_time(time1, time2) {
        let l1 = time1.length;
        let l2 = time2.length;
        let d1 = time1;
        let d2 = time2;
        if (l1 < l2) {
            d2 = d2.substring(0, l1);
        }
        if (l1 > l2) {
            d1 = d1.substring(0, l2);
        }
        return d1 == d2;
    }


    run_all_tests(folder = default_folder) {
        this.init_tests(folder = folder);
        let ok = 0;
        let failed = 0;
        let skipped = 0;
        let errors = [];
        this.tests.forEach(test => {
            let cal = test["Calendar"];
            let rd = test["RD"];
            let jd = test["JulianDate"];
            let jds = test["julian_string"];
            let gre = test["gregorian_string"];

            let indra_text = IndraTime.julianToISO(jd);
            let indra_jd = IndraTime.ISOTojulian(indra_text);
            let indra_human = IndraTime.julianToStringTime(jd);

            let res = "";
            it = indra_text;
            if (it.endsWith(" BC")) {
                it = "-" + indra_text.substring(0, indra_text.length - 3);
            }

            // console.log(`cal: ${cal}, rd: ${rd}, jd: ${jd}, jds: ${jds}, gre: ${gre}, indra_text: ${indra_text}, indra_jd: ${indra_jd}, indra_human: ${indra_human}`);
            if (this.cmp_time(jds, it)) {
                res += "[JD]";
            }
            if (this.cmp_time(gre, it)) {
                res += "[GD]";
            }
            if (res == "") {
                res = "Error";
                failed += 1;
                let err_msg = `Both ${jds} and ${gre} are not equal to ${it}`;
                errors.push(err_msg);
            } else {
                ok += 1;
            }

            if (indra_jd != jd) {
                res += `[JD-Error: ${indra_jd} != ${jd}]`;
                failed += 1;
                let err_msg = `Julian Date conversion failed: ${indra_jd} != ${jd}`;
                errors.push(err_msg);
            } else {
                ok += 1;
            }
        });
        let result = {
            "num_ok": ok,
            "num_failed": failed,
            "num_skipped": skipped,
            "errors": errors
        };
        return result;
    }
}

// check command line arguments --folder=<folder_name> --include_failure_cases=<true/false>
let folder = default_folder;
let include_failure_cases = false;

process.argv.forEach((val, index) => {
    if (val.startsWith("--folder=")) {
        folder = val.split("=")[1];
    }
});

let it = new IndraTests()
let result = [it.run_all_tests(folder = folder)];

console.log("#$#$# Result #$#$#")
console.log(JSON.stringify(result, null, 2));