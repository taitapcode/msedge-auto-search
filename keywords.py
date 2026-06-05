import random
import sqlite3
import sys
from pathlib import Path

NUMBER_OF_KEYWORDS = 30
DEFAULT_KEYWORDS = ["Cloud 3.0 architectures", "Multiagent AI systems"]

BASE = Path(__file__).resolve().parent
KEYWORDS_TXT = BASE / "keywords.txt"
DB_FILE = BASE / "keywords.db"


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
    conn.close()
    if not rows:
        print("(no keywords)")
        return
    for word, count in rows:
        print(f"{count:4d}  {word}")


def cmd_seed():
    conn = _get_db()
    words = _load_words_from_txt()
    conn.executemany(
        "INSERT OR IGNORE INTO keywords (word) VALUES (?)",
        [(w,) for w in words],
    )
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]
    conn.close()
    print(f"seeded {len(words)} words from {KEYWORDS_TXT.name}; total in db: {n}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("usage: python keywords.py <add|list|seed> [...]")
        sys.exit(1)

    match args[0]:
        case "add":
            if len(args) < 2:
                print("usage: python keywords.py add <keyword>")
                sys.exit(1)
            print(add_keyword(" ".join(args[1:])))
        case "list":
            cmd_list()
        case "seed":
            cmd_seed()
        case _:
            print(f"unknown command: {args[0]}")
            sys.exit(1)
