import argparse
import os
import random
import signal
import subprocess
import sys
import time
from pathlib import Path

from keywords import (
    increment_usage,
    load_keyword_data,
    save_keyword_data,
    select_keywords,
)

NUMBER_OF_KEYWORDS = 30
running = True
terminal_state = None

# Locate isolated profile in XDG Data share
XDG_DATA = (
    Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    / "msedge-auto-search"
)
BOT_PROFILE_DIR = XDG_DATA / "edge_bot_profile"
BOT_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

# OPTIMIZED FLAGS FOR BOT BROWSER
EDGE_COMMAND = [
    "microsoft-edge-stable",
    f"--user-data-dir={BOT_PROFILE_DIR}",
    "--no-first-run",  # Skip welcome screen / first-run setup wizard
    "--no-default-browser-check",  # Disable default browser check notification
    "--password-store=basic",  # Skip GNOME/KDE keyring unlock prompt on Linux
    "--disable-blink-features=AutomationControlled",  # Limit Microsoft AI detection of bot-controlled browser
    "--disable-popup-blocking",  # Disable popup blocking to prevent script hangs
    "--disable-features=EdgeShopping,EdgeWallet,EdgeSidebarEnhancedSidePanel,msHubApps",  # Disable shopping, wallet, cluttered sidebar features
]


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
    run_cmd(["pkill", "ydotoold"])
    log("ydotoold stopped.")


def close_browser():
    log("Closing bot Microsoft Edge...")
    run_cmd(["pkill", "-f", str(BOT_PROFILE_DIR)])
    time.sleep(1)
    log("Bot browser closed.")


def handle_exit(_sig, _frame):
    global running
    running = False
    log("Script interrupted unexpectedly.")
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
    log("Sudo authentication OK.")


def open_browser_manually():
    log("========================================================")
    log(" Launching Microsoft Edge in MANUAL MODE (Optimized)")
    log(f" Profile path: {BOT_PROFILE_DIR}")
    log(" -> Please log into your Microsoft Rewards account.")
    log(" -> After finishing, close the Edge window to save session.")
    log("========================================================")
    # Use optimized command with flags
    subprocess.run(
        EDGE_COMMAND,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    log(" Session state saved successfully!")


def automate_search():
    warmup_sudo()
    disable_echoctl()
    start_ydotoold()
    log("Opening Microsoft Edge (Optimized automation mode)...")

    # Use optimized command with flags
    subprocess.Popen(
        EDGE_COMMAND,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    words, usage = load_keyword_data()
    keywords = select_keywords(words, usage, NUMBER_OF_KEYWORDS)
    log(f"Loaded {len(keywords)} keywords. Waiting for browser to stabilize...")
    sleep_interruptible(3)

    for i, word in enumerate(keywords):
        if not running:
            break
        log(f"Searching [{i+1}/{len(keywords)}]: {word}")

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

    parser = argparse.ArgumentParser(description="msedge-auto-search PC interface")
    parser.add_argument(
        "--open", action="store_true", help="Open Edge manually for configuration/login"
    )
    args = parser.parse_args()

    if args.open:
        open_browser_manually()
    else:
        automate_search()
