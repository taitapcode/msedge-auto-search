import subprocess
import time
import random
import sys
import signal

NUMBER_OF_KEYWORDS = 2
running = True


def get_keywords():
    try:
        with open("keywords.txt", "r", encoding="utf-8") as f:
            words = list(set(line.strip() for line in f if line.strip()))
            random.shuffle(words)
            return words[:NUMBER_OF_KEYWORDS]
    except FileNotFoundError:
        return ["Cloud 3.0 architectures", "Multiagent AI systems"]


def run_ydotool(args):
    if not running:
        return
    subprocess.run(["ydotool"] + args)


def start_ydotoold():
    print("🔧 Đang khởi động ydotoold daemon...")
    subprocess.Popen(
        [
            "sudo",
            "ydotoold",
            "--socket-path=/run/user/1000/.ydotool_socket",
            "--socket-perm=0666",
        ]
    )
    time.sleep(1)
    print("✅ ydotoold đã sẵn sàng.")


def stop_ydotoold():
    print("🔧 Đang tắt ydotoold daemon...")
    subprocess.run(["sudo", "pkill", "ydotoold"])
    print("✅ ydotoold đã dừng.")


def close_browser():
    print("🌐 Đang đóng Microsoft Edge...")
    subprocess.run(["pkill", "-f", "msedge"])
    time.sleep(1)
    print("✅ Đã đóng trình duyệt.")


def handle_exit(sig, frame):
    global running
    running = False
    print("\n🛑 Script đã dừng.")
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
    print(f"🖱️ Đang cuộn trang {'xuống' if direction == 'down' else 'lên'} từ từ...")
    steps = random.randint(5, 15)
    val = -2 if direction == "down" else 2
    for _ in range(steps):
        if not running:
            return
        run_ydotool(["mousemove", "-w", "-x", "0", "-y", str(val)])
        sleep_interruptible(random.uniform(0.1, 0.2))


def warmup_sudo():
    print("🔑 Yêu cầu xác thực sudo (nhập mật khẩu nếu cần)...")
    result = subprocess.run(["sudo", "-v"])
    if result.returncode != 0:
        print("❌ Xác thực sudo thất bại. Thoát.")
        sys.exit(1)
    print("✅ Xác thực sudo thành công.")


def automate_search():
    warmup_sudo()
    start_ydotoold()
    print("🚀 Đang khởi động Microsoft Edge...")
    subprocess.Popen(["microsoft-edge-stable"])

    keywords = get_keywords()
    print(f"✅ Đã nạp {len(keywords)} từ khóa ngẫu nhiên. Đang đợi trình duyệt...")
    sleep_interruptible(3)

    for i, word in enumerate(keywords):
        if not running:
            break
        print(f"🔍 [{i+1}/{len(keywords)}] Đang tìm: {word}")

        run_ydotool(["key", "29:1", "38:1", "38:0", "29:0"])
        sleep_interruptible(0.5)

        run_ydotool(["key", "29:1", "30:1", "30:0", "29:0"])
        run_ydotool(["key", "14:1", "14:0"])
        sleep_interruptible(0.5)

        run_ydotool(["type", word])
        sleep_interruptible(0.6)
        run_ydotool(["key", "28:1", "28:0"])

        sleep_interruptible(random.uniform(1, 2))

        smooth_scroll(direction="down")
        sleep_interruptible(random.uniform(0.5, 1))
        smooth_scroll(direction="up")

        delay = random.uniform(5, 8)
        print(f"⏳ Nghỉ {delay:.2f} giây trước khi sang từ tiếp theo...")
        sleep_interruptible(delay)

    if running:
        print("🎉 Hoàn thành tất cả từ khóa!")
        close_browser()
        stop_ydotoold()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    automate_search()
