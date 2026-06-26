import argparse
import random
import re
import signal
import subprocess
import sys
import time
from urllib.parse import quote_plus

from keywords import (
    increment_usage,
    load_keyword_data,
    save_keyword_data,
    select_keywords,
)

NUMBER_OF_KEYWORDS = 20
PREFERRED_PACKAGE = "com.microsoft.bing"
DEFAULT_TAP_X = None
DEFAULT_TAP_Y = 50
PRE_TAP_SCROLL = True

running = True
shell_requires_sudo = False


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
            print("Cannot start Waydroid session.")
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
    end_y = int(height * 0.5)
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
    word_list, usage = load_keyword_data()
    keywords = select_keywords(word_list, usage, args.keywords)
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
            increment_usage(usage, word)
        else:
            open_search(word, package_name=package_name)
        sleep_interruptible(random.uniform(1, 2))
        smooth_scroll(width, height, direction="down")
        smooth_scroll(width, height, direction="up")

    if running:
        waydroid_shell(["input", "keyevent", "3"])
    save_keyword_data(word_list, usage)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    automate_search(parse_args())
