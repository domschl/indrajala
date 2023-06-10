import unittest

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


if __name__ == "__main__":
    unittest.main()
