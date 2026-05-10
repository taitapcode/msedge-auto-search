import json
import random
import signal
import subprocess
import sys
import time
from pathlib import Path

NUMBER_OF_KEYWORDS = 30
DEFAULT_KEYWORDS = ["Cloud 3.0 architectures", "Multiagent AI systems"]
KEYWORDS_FILE = Path(__file__).resolve().parent / "keywords.json"
running = True
terminal_state = None


def run_cmd(cmd, **kwargs):
    if "stdout" not in kwargs:
        kwargs["stdout"] = subprocess.DEVNULL
    if "stderr" not in kwargs:
        kwargs["stderr"] = subprocess.DEVNULL
    return subprocess.run(cmd, **kwargs)


def log(message):
    if sys.stdout.isatty():
        sys.stdout.write("\r\033[2K")
    sys.stdout.write(f"{message}\n")
    sys.stdout.flush()


def disable_echoctl():
    global terminal_state
    if not sys.stdin.isatty():
        return
    result = run_cmd(
        ["stty", "-g"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        return
    terminal_state = result.stdout.strip()
    if terminal_state:
        run_cmd(["stty", "-echoctl"], stdout=None, stderr=None)


def restore_terminal():
    global terminal_state
    if not terminal_state:
        return
    run_cmd(["stty", terminal_state], stdout=None, stderr=None)
    terminal_state = None


def load_keyword_data():
    keywords = DEFAULT_KEYWORDS[:]
    usage = {}
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
            raw_usage = data.get("usage", {}) if isinstance(data.get("usage"), dict) else {}
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

    deduped = list(dict.fromkeys(words))
    keywords = deduped or keywords

    clean_usage = {}
    if isinstance(raw_usage, dict):
        for key, value in raw_usage.items():
            if not isinstance(key, str):
                continue
            count = 0
            if isinstance(value, dict):
                count_value = value.get("usage", 0)
            else:
                count_value = value
            try:
                count = int(count_value)
            except (TypeError, ValueError):
                count = 0
            clean_usage[key.strip()] = max(count, 0)

    return keywords, clean_usage


def save_keyword_data(keywords, usage):
    payload = {}
    for word in keywords:
        count = usage.get(word, 0)
        payload[word] = {"usage": int(count)}
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


def run_ydotool(args):
    if not running:
        return
    run_cmd(["ydotool"] + args)


def start_ydotoold():
    log("Starting ydotoold daemon...")
    subprocess.Popen(
        [
            "sudo",
            "ydotoold",
            "--socket-path=/run/user/1000/.ydotool_socket",
            "--socket-perm=0666",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)
    log("ydotoold is ready.")


def stop_ydotoold():
    log("Stopping ydotoold daemon...")
    run_cmd(["sudo", "pkill", "ydotoold"])
    log("ydotoold stopped.")


def close_browser():
    log("Closing Microsoft Edge...")
    run_cmd(["pkill", "-f", "msedge"])
    time.sleep(1)
    log("Browser closed.")


def handle_exit(_sig, _frame):
    global running
    running = False
    log("Script stopped.")
    restore_terminal()
    close_browser()
    stop_ydotoold()
    sys.exit(0)


def sleep_interruptible(seconds):
    interval = 0.1
    elapsed = 0
    while elapsed < seconds:
        if not running:
            return
        time.sleep(interval)
        elapsed += interval


def smooth_scroll(direction="down"):
    log(f"Scrolling {'down' if direction == 'down' else 'up'}...")
    steps = random.randint(5, 15)
    val = -2 if direction == "down" else 2
    for _ in range(steps):
        if not running:
            return
        run_ydotool(["mousemove", "-w", "-x", "0", "-y", str(val)])
        sleep_interruptible(random.uniform(0.1, 0.2))


def warmup_sudo():
    log("Requesting sudo authentication...")
    result = run_cmd(["sudo", "-v"], stdout=None, stderr=None)
    if result.returncode != 0:
        log("Sudo authentication failed. Exiting.")
        sys.exit(1)
    log("Sudo authentication ok.")


def automate_search():
    warmup_sudo()
    disable_echoctl()
    start_ydotoold()
    log("Launching Microsoft Edge...")
    subprocess.Popen(
        ["microsoft-edge-stable"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    words, usage = load_keyword_data()
    keywords = select_keywords(words, usage, NUMBER_OF_KEYWORDS)
    log(f"Loaded {len(keywords)} keywords. Waiting for browser...")
    sleep_interruptible(3)

    for i, word in enumerate(keywords):
        if not running:
            break
        log(f"Search [{i+1}/{len(keywords)}]: {word}")

        run_ydotool(["key", "29:1", "38:1", "38:0", "29:0"])
        sleep_interruptible(0.5)

        run_ydotool(["key", "29:1", "30:1", "30:0", "29:0"])
        run_ydotool(["key", "14:1", "14:0"])
        sleep_interruptible(0.5)

        run_ydotool(["type", word])
        sleep_interruptible(0.6)
        run_ydotool(["key", "28:1", "28:0"])
        increment_usage(usage, word)

        sleep_interruptible(random.uniform(1, 2))

        smooth_scroll(direction="down")
        sleep_interruptible(random.uniform(0.5, 1))
        smooth_scroll(direction="up")

    if running:
        log("Finished all keywords.")
        close_browser()
        stop_ydotoold()
    save_keyword_data(words, usage)
    restore_terminal()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    automate_search()
