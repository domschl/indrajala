"use strict";
// Indralib shared ES6 module

import { IndraTime } from "../scripts/indra_time.js";
import { IndraEvent } from "../scripts/indralib.js";
import fs from 'fs';

const default_folder = "../../../test_data/domain"
function load_test_Data(testDataFolder = default_folder, include_failure_cases = false) {
    const filePath = testDataFolder + "/domain_publish_subscribe_data.json";
    const fileContent = fs.readFileSync(filePath, 'utf-8');
    const jsonData = JSON.parse(fileContent);
    if (include_failure_cases) {
        const filePath = testDataFolder + "/domain_failure_cases.json";
        const fileContent = fs.readFileSync(filePath, 'utf-8');
        const failureCases = JSON.parse(fileContent);
        jsonData.push(...failureCases);
    }
    // console.log(jsonData);
    return jsonData;
}



export class IndraTests {
    init_dom_tests(folder = default_folder, include_failure_cases = false) {
        this.dom_tests = load_test_Data(folder, include_failure_cases);
        this.errors = [];
        this.num_ok = 0;
        this.num_failed = 0;
        this.num_skipped = 0;
    }

    run_all_tests(folder = default_folder, include_failure_cases = false) {
        this.init_dom_tests(folder = folder, include_failure_cases = include_failure_cases);
        let ok = 0;
        let failed = 0;
        let skipped = 0;
        let errors = [];
        this.dom_tests.forEach(test => {
            let pub = test["publish"];
            let sub = test["subscribe"];
            let res = test["result"];
            if (IndraEvent.mqcmp(pub, sub) == res) {
                this.num_ok += 1;
                ok += 1;
            } else {
                console.log("Test failed: " + test);
                this.num_failed += 1;
                failed += 1;
                this.errors.push(test);
                let err_msg = `Test failed: mqcmp(${pub}, ${sub}) != ${res}, expected ${res}, got ${IndraEvent.mqcmp(pub, sub)}`;
                errors.push(err_msg);
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
    } else if (val.startsWith("--include_failure_cases=")) {
        include_failure_cases = val.split("=")[1] === 'true';
    }
});

let it = new IndraTests()
let result = [it.run_all_tests(folder = folder, include_failure_cases = include_failure_cases)];

console.log("#$#$# Result #$#$#")
console.log(JSON.stringify(result, null, 2));