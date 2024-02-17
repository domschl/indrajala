import sys
import json
import time

if __name__ == "__main__":
    print("Starting zero_test.py")
    if len(sys.argv) != 3:
        print("Usage: zero_test.py <main_process_zeromq_port> <json_config_string>")
        sys.exit(1)
    port = int(sys.argv[1])
    try:
        if sys.argv[2][0] == "'" and sys.argv[2][-1] == "'":
            config = json.loads(sys.argv[2][1:-1])
        else:
            config = json.loads(sys.argv[2])
    except Exception as e:
        print("JSON Error: ", e)
        sys.exit(1)

    while True:
        time.sleep(1)
