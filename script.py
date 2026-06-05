import random
import signal
import subprocess
import sys
import time

from keywords import (
    NUMBER_OF_KEYWORDS,
    increment_usage,
    load_keyword_data,
    save_keyword_data,
    select_keywords,
)

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
