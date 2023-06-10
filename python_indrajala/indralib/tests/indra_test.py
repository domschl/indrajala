import unittest
from datetime import datetime, timedelta, timezone
import sys
import os

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
print(path)
sys.path.append(path)

from indra_event import IndraEvent


class TestIndraEvent(unittest.TestCase):
    def test_mqcmp(self):
        td = [
            ("abc", "abc", True),
            ("ab", "abc", False),
            ("ab", "ab+", True),
            ("abcd/dfew", "abcd", False),
            ("ba", "bdc/ds", False),
            ("abc/def", "abc/+", True),
            ("abc/def", "asdf/+/asdf", False),
            ("abc/def/asdf", "abc/+/asdf", True),
            ("abc/def/ghi", "+/+/+", True),
            ("abc/def/ghi", "+/+/", False),
            ("abc/def/ghi", "+/+/+/+", False),
            ("abc/def/ghi", "+/#", True),
            ("abc/def/ghi", "+/+/#", True),
            ("abc/def/ghi", "+/+/+/#", False),
        ]
        for t in td:
            pub = t[0]
            sub = t[1]
            result = IndraEvent.mqcmp(pub, sub)
            self.assertEqual(
                result, t[2], f"pub:{pub}, sub:{sub} = {t[2]} != ground truth"
            )


test_year = 2020


class TestFracyearConversion(unittest.TestCase):
    def assertDateTimeAlmostEqual(self, dt1, dt2, delta_seconds=1):
        print(dt1, dt2)
        delta = timedelta(seconds=delta_seconds)
        diff = abs(dt1 - dt2)
        self.assertLessEqual(diff, delta)

    def test_fracyear2datetime(self):
        # Test fracyear2datetime function
        test_data = [
            (test_year, datetime(test_year, 1, 1, 0, 0, tzinfo=timezone.utc)),
            (
                test_year + 0.1,
                datetime(test_year, 2, 6, 12, 36, tzinfo=timezone.utc),
            ),
            (test_year + 0.2, datetime(test_year, 3, 14, 1, 12, tzinfo=timezone.utc)),
            (test_year + 0.3, datetime(test_year, 4, 19, 13, 48, tzinfo=timezone.utc)),
            (test_year + 0.4, datetime(test_year, 5, 26, 2, 24, tzinfo=timezone.utc)),
            (test_year + 0.5, datetime(test_year, 7, 1, 15, 0, tzinfo=timezone.utc)),
            (test_year + 0.6, datetime(test_year, 8, 7, 3, 36, tzinfo=timezone.utc)),
            (test_year + 0.7, datetime(test_year, 9, 12, 16, 12, tzinfo=timezone.utc)),
            (test_year + 0.8, datetime(test_year, 10, 19, 4, 48, tzinfo=timezone.utc)),
            (test_year + 0.9, datetime(test_year, 11, 24, 17, 24, tzinfo=timezone.utc)),
            # (test_year + 1.0, datetime(test_year + 1, 1, 1, 6, 0))
            # Add more test cases here if needed
        ]

        for fy, expected_datetime in test_data:
            result = IndraEvent.fracyear2datetime(fy)
            self.assertDateTimeAlmostEqual(result, expected_datetime)

    def test_datetime2fracyear(self):
        # Test datetime2fracyear function
        test_data = [
            (datetime(test_year, 1, 1, 0, 0, tzinfo=timezone.utc), test_year + 0.0),
            (datetime(test_year, 2, 6, 12, 36, tzinfo=timezone.utc), test_year + 0.1),
            (datetime(test_year, 3, 14, 1, 12, tzinfo=timezone.utc), test_year + 0.2),
            (datetime(test_year, 4, 19, 13, 48, tzinfo=timezone.utc), test_year + 0.3),
            (datetime(test_year, 5, 26, 2, 24, tzinfo=timezone.utc), test_year + 0.4),
            (datetime(test_year, 7, 1, 15, 0, tzinfo=timezone.utc), test_year + 0.5),
            (datetime(test_year, 8, 7, 3, 36, tzinfo=timezone.utc), test_year + 0.6),
            (datetime(test_year, 9, 12, 16, 12, tzinfo=timezone.utc), test_year + 0.7),
            (datetime(test_year, 10, 19, 4, 48, tzinfo=timezone.utc), test_year + 0.8),
            (datetime(test_year, 11, 24, 17, 24, tzinfo=timezone.utc), test_year + 0.9),
            # (datetime(test_year + 1, 1, 1, 6, 0), test_year + 1.0)
            # Add more test cases here if needed
        ]

        for dt, expected_fracyear in test_data:
            result = IndraEvent.datetime2fracyear(dt)
            self.assertAlmostEqual(result, expected_fracyear, delta=0.0001)


if __name__ == "__main__":
    unittest.main()
