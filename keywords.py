import random
import sqlite3
import sys
import os
from pathlib import Path

DEFAULT_KEYWORDS = ["Cloud 3.0 architectures", "Multiagent AI systems"]


def _resolve_paths():
    base_dir = Path(__file__).resolve().parent
    # Check write permission in current directory (normal run)
    try:
        test_file = base_dir / ".nix_write_test"
        test_file.touch()
        test_file.unlink()
        return base_dir / "keywords.txt", base_dir / "keywords.db"
    except (OSError, IOError):
        # If running in Nix Store (Read-Only), fall back to XDG personal storage
        xdg_data = (
            Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
            / "msedge-auto-search"
        )
        xdg_data.mkdir(parents=True, exist_ok=True)

        dest_txt = xdg_data / "keywords.txt"
        # Copy default keyword file from Nix package to personal directory if not present
        if not dest_txt.exists() and (base_dir / "keywords.txt").exists():
            import shutil

            shutil.copy(base_dir / "keywords.txt", dest_txt)

        return dest_txt, xdg_data / "keywords.db"


KEYWORDS_TXT, DB_FILE = _resolve_paths()


def _get_db():
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS keywords (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            word  TEXT UNIQUE NOT NULL,
            usage INTEGER DEFAULT 0
        )"""
    )
    conn.commit()
    return conn


def _load_words_from_txt():
    try:
        text = KEYWORDS_TXT.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return DEFAULT_KEYWORDS[:]
    words = []
    for line in text.splitlines():
        w = line.strip()
        if w:
            words.append(w)
    return list(dict.fromkeys(words)) or DEFAULT_KEYWORDS[:]


def _ensure_seeded(conn):
    count = conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]
    if count > 0:
        return
    conn.executemany(
        "INSERT OR IGNORE INTO keywords (word) VALUES (?)",
        [(w,) for w in _load_words_from_txt()],
    )
    conn.commit()


def load_keyword_data():
    conn = _get_db()
    _ensure_seeded(conn)
    rows = conn.execute("SELECT word, usage FROM keywords ORDER BY id").fetchall()
    conn.close()
    words = []
    usage = {}
    for word, count in rows:
        words.append(word)
        usage[word] = count
    return words, usage


def save_keyword_data(keywords, usage):
    conn = _get_db()
    conn.executemany(
        "INSERT INTO keywords (word, usage) VALUES (?, ?) "
        "ON CONFLICT(word) DO UPDATE SET usage = excluded.usage",
        [(w, int(usage.get(w, 0))) for w in keywords],
    )
    conn.commit()
    conn.close()


def select_keywords(words, usage, limit):
    shuffled = list(words)
    random.shuffle(shuffled)
    shuffled.sort(key=lambda word: usage.get(word, 0))
    return shuffled[:limit]


def increment_usage(usage, word):
    usage[word] = usage.get(word, 0) + 1


def add_keyword(word):
    word = word.strip()
    if not word:
        return "error: empty keyword"
    try:
        text = KEYWORDS_TXT.read_text(encoding="utf-8")
    except FileNotFoundError:
        text = ""
    existing = set(line.strip() for line in text.splitlines() if line.strip())
    if word in existing:
        return f"exists: {word}"
    with KEYWORDS_TXT.open("a", encoding="utf-8") as f:
        f.write(f"{word}\n")
    conn = _get_db()
    conn.execute("INSERT OR IGNORE INTO keywords (word) VALUES (?)", (word,))
    conn.commit()
    conn.close()
    return f"added: {word}"


def cmd_list():
    conn = _get_db()
    _ensure_seeded(conn)
    rows = conn.execute(
        "SELECT word, usage FROM keywords ORDER BY usage ASC, word ASC"
    ).fetchall()
