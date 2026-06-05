import argparse
import json
import random
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

NUMBER_OF_KEYWORDS = 20
DEFAULT_KEYWORDS = [
    "Cloud 3.0 architectures",
    "Multiagent AI systems",
]
KEYWORDS_FILE = Path(__file__).resolve().parent / "keywords.json"
PREFERRED_PACKAGE = "com.microsoft.bing"
DEFAULT_TAP_X = None
DEFAULT_TAP_Y = 50
PRE_TAP_SCROLL = True

running = True
shell_requires_sudo = False
keyword_list = []
keyword_usage = {}


def load_keyword_data():
    try:
        data = json.loads(KEYWORDS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = None

    raw_keywords = []
    raw_usage = {}

    if isinstance(data, list):
        raw_keywords = data
    elif isinstance(data, dict):
        if "keywords" in data or "usage" in data:
            raw_keywords = data.get("keywords", [])
            raw_usage = (
                data.get("usage", {}) if isinstance(data.get("usage"), dict) else {}
            )
        else:
            raw_keywords = list(data.keys())
            raw_usage = data

    words = []
    for item in raw_keywords:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if value:
            words.append(value)
    words = list(dict.fromkeys(words))
    if not words:
        words = DEFAULT_KEYWORDS[:]

    usage = {}
    if isinstance(raw_usage, dict):
        for key, value in raw_usage.items():
            if not isinstance(key, str):
                continue
            count_value = value.get("usage", 0) if isinstance(value, dict) else value
            try:
                usage[key.strip()] = max(int(count_value), 0)
            except (TypeError, ValueError):
                usage[key.strip()] = 0

    return words, usage


def save_keyword_data(keywords, usage):
    payload = {}
    for word in keywords:
        payload[word] = {"usage": int(usage.get(word, 0))}
    try:
        KEYWORDS_FILE.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        return


def select_keywords(words, usage, limit):
    shuffled = list(words)
    random.shuffle(shuffled)
    shuffled.sort(key=lambda word: usage.get(word, 0))
    return shuffled[:limit]


def increment_usage(usage, word):
    usage[word] = usage.get(word, 0) + 1


def warmup_sudo():
    result = subprocess.run(["sudo", "-v"])
    if result.returncode != 0:
        print("Sudo authentication failed.")
        sys.exit(1)


def waydroid_shell(cmd_args, capture_output=False):
    if not running:
        return None
    base_cmd = ["waydroid", "shell", "--"] + cmd_args
    if shell_requires_sudo:
        base_cmd = ["sudo"] + base_cmd
    return subprocess.run(
        base_cmd,
        capture_output=capture_output,
        text=True,
    )


def is_session_running():
    result = subprocess.run(
        ["waydroid", "status"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and "Session: RUNNING" in result.stdout


def ensure_waydroid_session():
    if is_session_running():
        return
    result = subprocess.run(
        ["waydroid", "session", "start"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        combined = (result.stdout or "") + (result.stderr or "")
        if "Already tracking a session" not in combined:
            print("Failed to start Waydroid session.")
            print(combined.strip())
            sys.exit(1)
    for _ in range(15):
        if is_session_running():
            return
        time.sleep(1)


def detect_preferred_package():
    result = subprocess.run(
        ["waydroid", "app", "list"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    installed = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("packageName:"):
            installed.add(line.split(":", 1)[1].strip())
    return PREFERRED_PACKAGE if PREFERRED_PACKAGE in installed else None


def launch_app(package_name):
    if not package_name:
        return False
    result = subprocess.run(["waydroid", "app", "launch", package_name])
    return result.returncode == 0


def detect_shell_privileges():
    global shell_requires_sudo
    result = subprocess.run(
        ["waydroid", "shell", "--", "id"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        shell_requires_sudo = False
        return
    combined = (result.stdout or "") + (result.stderr or "")
    if "needs root access" in combined.lower():
        shell_requires_sudo = True
        warmup_sudo()


def get_screen_size():
    result = waydroid_shell(["wm", "size"], capture_output=True)
    if not result or result.returncode != 0:
        return 1080, 1920
    match = re.search(r"Physical size:\s*(\d+)x(\d+)", result.stdout)
    if not match:
        return 1080, 1920
    return int(match.group(1)), int(match.group(2))


def open_search(query, package_name=None):
    url = f"https://www.bing.com/search?q={quote_plus(query)}"
    cmd = ["am", "start", "-a", "android.intent.action.VIEW", "-d", url]
    if package_name:
        cmd.extend(["-p", package_name])
    waydroid_shell(cmd)


def sleep_interruptible(seconds):
    interval = 0.1
    elapsed = 0
    while elapsed < seconds:
        if not running:
            return
        time.sleep(interval)
        elapsed += interval


def tap(x, y):
    waydroid_shell(["input", "tap", str(x), str(y)])


def encode_input_text(text):
    return text.replace(" ", "%s")


def clear_text(length):
    waydroid_shell(["input", "keyevent", "123"])
    count = max(length + 5, 32)
    waydroid_shell(["input", "keyevent"] + ["67"] * count)


def smooth_scroll(width, height, direction="down"):
    steps = random.randint(3, 5)
    x = width // 2
    down_start = int(height * 0.8)
    down_end = int(height * 0.3)
    if direction == "down":
        start_y, end_y = down_start, down_end
    else:
        start_y, end_y = down_end, down_start
    for _ in range(steps):
        if not running:
            return
        duration = random.randint(150, 250)
        waydroid_shell(
            [
                "input",
                "swipe",
                str(x),
                str(start_y),
                str(x),
                str(end_y),
                str(duration),
            ]
        )
        sleep_interruptible(random.uniform(0.1, 0.3))


def pre_tap_scroll(width, height):
    x = width // 2
    start_y = int(height * 0.7)
    end_y = int(height * 0.3)
    waydroid_shell(
        [
            "input",
            "swipe",
            str(x),
            str(start_y),
            str(x),
            str(end_y),
            "180",
        ]
    )


def handle_exit(sig, frame):
    global running
    running = False
    waydroid_shell(["input", "keyevent", "3"])
    sys.exit(0)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", type=int, default=NUMBER_OF_KEYWORDS)
    return parser.parse_args()


def get_tap_coords(width, height, args):
    x = int(width * 0.5)
    y = DEFAULT_TAP_Y
    return x, y


def automate_search(args):
    warmup_sudo()
    ensure_waydroid_session()
    detect_shell_privileges()
    width, height = get_screen_size()
    package_name = detect_preferred_package()
    global keyword_list, keyword_usage
    keyword_list, keyword_usage = load_keyword_data()
    keywords = select_keywords(keyword_list, keyword_usage, args.keywords)
    tap_x, tap_y = get_tap_coords(width, height, args)
    time.sleep(5)

    for i, word in enumerate(keywords, start=1):
        if not running:
            break
        print(f"Search [{i}/{len(keywords)}]: {word}")
        if package_name and launch_app(package_name):
            sleep_interruptible(random.uniform(1.5, 2.5))
            if PRE_TAP_SCROLL and i == 1:
                pre_tap_scroll(width, height)
                sleep_interruptible(0.3)
            tap(tap_x, tap_y)
            sleep_interruptible(0.4)
            clear_text(len(word))
            waydroid_shell(["input", "text", encode_input_text(word)])
            sleep_interruptible(0.2)
            waydroid_shell(["input", "keyevent", "66"])
            increment_usage(keyword_usage, word)
        else:
            open_search(word, package_name=package_name)
        sleep_interruptible(random.uniform(1, 2))
        smooth_scroll(width, height, direction="down")
        smooth_scroll(width, height, direction="up")
        # delay = random.uniform(3, 5)
        # print(f"Waiting {delay:.2f}s before next query")
        # sleep_interruptible(delay)

    if running:
        waydroid_shell(["input", "keyevent", "3"])
    save_keyword_data(keyword_list, keyword_usage)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    automate_search(parse_args())
