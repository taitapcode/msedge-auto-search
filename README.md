# msedge-auto-search

Automates Microsoft Edge searches with randomized keywords to earn Rewards points.

## Usage

```bash
# Run automation
python script.py

# Keyword management
python keywords.py list          # show all keywords + usage counts
python keywords.py add "..."     # add a new keyword
python keywords.py seed          # re-seed DB from keywords.txt

# Run inside Waydroid container
python waydroid.py [--keywords N]

# Query the DB directly
sqlite3 keywords.db "SELECT * FROM keywords ORDER BY usage ASC;"
```

## How it works

1. `script.py` / `waydroid.py` loads keywords from SQLite, picks the least-used ones, and performs searches via `ydotool`
2. Each search increments the usage counter for that keyword
3. Usage is persisted to SQLite so the next run prioritizes under-used keywords

## Requirements

- `ydotool` (for keyboard/mouse simulation)
- `microsoft-edge-stable`
- `waydroid` (optional, for running inside Android container)
- Python 3.10+ (uses `match` statement)
