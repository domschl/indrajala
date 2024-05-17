"use strict";
// Indralib shared ES6 module

import { IndraTime } from "../scripts/indra_time.js";

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
    { "year": -586, "month": 7, "day": 24 },
    { "year": -168, "month": 12, "day": 5 },
    { "year": 70, "month": 9, "day": 24 },
    { "year": 135, "month": 10, "day": 2 },
    { "year": 470, "month": 1, "day": 8 },
    { "year": 576, "month": 5, "day": 20 },
    { "year": 694, "month": 11, "day": 10 },
    { "year": 1013, "month": 4, "day": 25 },
    { "year": 1096, "month": 5, "day": 24 },
    { "year": 1190, "month": 3, "day": 23 },
    { "year": 1240, "month": 3, "day": 10 },
    { "year": 1288, "month": 4, "day": 2 },
    { "year": 1298, "month": 4, "day": 27 },
    { "year": 1391, "month": 6, "day": 12 },
    { "year": 1436, "month": 2, "day": 3 },
    { "year": 1492, "month": 4, "day": 9 },
    { "year": 1553, "month": 9, "day": 19 },
    { "year": 1560, "month": 3, "day": 5 },
    { "year": 1648, "month": 6, "day": 10 },
    { "year": 1680, "month": 6, "day": 30 },
    { "year": 1716, "month": 7, "day": 24 },
    { "year": 1768, "month": 6, "day": 19 },
    { "year": 1819, "month": 8, "day": 2 },
    { "year": 1839, "month": 3, "day": 27 },
    { "year": 1903, "month": 4, "day": 19 },
    { "year": 1929, "month": 8, "day": 25 },
    { "year": 1941, "month": 9, "day": 29 },
    { "year": 1943, "month": 4, "day": 19 },
    { "year": 1943, "month": 10, "day": 7 },
    { "year": 1992, "month": 3, "day": 17 },
    { "year": 1996, "month": 2, "day": 25 },
    { "year": 2038, "month": 11, "day": 10 },
    { "year": 2094, "month": 7, "day": 18 },
]

julian_table = [
    { "year": -586, "month": 7, "day": 30 },
    { "year": -168, "month": 12, "day": 8 },
    { "year": 70, "month": 9, "day": 26 },
    { "year": 135, "month": 10, "day": 3 },
    { "year": 470, "month": 1, "day": 7 },
    { "year": 576, "month": 5, "day": 18 },
    { "year": 694, "month": 11, "day": 7 },
    { "year": 1013, "month": 4, "day": 19 },
    { "year": 1096, "month": 5, "day": 18 },
    { "year": 1190, "month": 3, "day": 16 },
    { "year": 1240, "month": 3, "day": 3 },
    { "year": 1288, "month": 3, "day": 26 },
    { "year": 1298, "month": 4, "day": 20 },
    { "year": 1391, "month": 6, "day": 4 },
    { "year": 1436, "month": 1, "day": 25 },
    { "year": 1492, "month": 3, "day": 31 },
    { "year": 1553, "month": 9, "day": 9 },
    { "year": 1560, "month": 2, "day": 24 },
    { "year": 1648, "month": 5, "day": 31 },
    { "year": 1680, "month": 6, "day": 20 },
    { "year": 1716, "month": 7, "day": 13 },
    { "year": 1768, "month": 6, "day": 8 },
    { "year": 1819, "month": 7, "day": 21 },
    { "year": 1839, "month": 3, "day": 15 },
    { "year": 1903, "month": 4, "day": 6 },
    { "year": 1929, "month": 8, "day": 12 },
    { "year": 1941, "month": 9, "day": 16 },
    { "year": 1943, "month": 4, "day": 6 },
    { "year": 1943, "month": 9, "day": 24 },
    { "year": 1992, "month": 3, "day": 4 },
    { "year": 1996, "month": 2, "day": 12 },
    { "year": 2038, "month": 10, "day": 28 },
    { "year": 2094, "month": 7, "day": 5 },
]

export class IndraTests {
    static run_all_tests() {
        IndraTests.test_time();
    }

    static test_time() {
        const it = new IndraTime();
        const jt = it.time_to_julian_gregorian(2021, 8, 13, 12, 1, 0, 0);
        console.log(jt);
        const dt = it.julian_to_time(jt);
        console.log(dt);
        const jt2 = it.time_to_julian(2021, 8, 13, 12, 1, 0, 0);
        console.log(jt2);
    }
}

IndraTests.run_all_tests();