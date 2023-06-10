from indra_event import IndraEvent


def test_mqcmp():
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
        if IndraEvent.mqcmp(pub, sub) != t[2]:
            print(f"pub:{pub}, sub:{sub} = {t[2]}!=ground truth")
            print("Fix your stuff first!")
            exit(-1)


test_mqcmp()
