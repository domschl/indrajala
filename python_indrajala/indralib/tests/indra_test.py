import unittest
from datetime import datetime, timedelta, timezone
import json
import sys
import os

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
# print(path)
sys.path.append(path)

from indra_event import IndraEvent


class TestIndraEvent(unittest.TestCase):
    def test_mqcmp(self):
        # read test data from domain_mqcmp.json:
        with open("mqcmp_data.json", "r") as f:
            td = json.load(f)
        for t in td:
            result = IndraEvent.mqcmp(t["pub"], t["sub"])
            self.assertEqual(
                result,
                t["result"],
                f"pub:{t['pub']}, sub:{t['sub']} = {result} != {t['result']} (ground truth)",
            )


test_year = 2020


class TestFracyearConversion(unittest.TestCase):
    def assertDateTimeAlmostEqual(self, dt1, dt2, delta_seconds=1):
        # print(dt1, dt2)
        delta = timedelta(seconds=delta_seconds)
        diff = abs(dt1 - dt2)
        self.assertLessEqual(diff, delta)

    def test_fracyear2datetime(self):
        # Test fracyear2datetime function
        with open("wp_decimal_time_data.json", "r") as f:
            td = json.load(f)

        for t in td:
            result = IndraEvent.fracyear2datetime(t["frac_year"])
            expected_datetime = datetime.fromisoformat(t["date"])
            print(result, expected_datetime)
            self.assertDateTimeAlmostEqual(result, expected_datetime)

    def test_datetime2fracyear(self):
        # Test datetime2fracyear function
        with open("wp_decimal_time_data.json", "r") as f:
            td = json.load(f)

        for t in td:
            dt = datetime.fromisoformat(t["date"])
            result = IndraEvent.datetime2fracyear(dt)
            expected_fracyear = t["frac_year"]
            self.assertAlmostEqual(result, expected_fracyear, delta=0.0001)


if __name__ == "__main__":
    unittest.main()
