# logger_txt.py

from datetime import datetime
import os

LOG_FILE = "system_log.txt"


def write_log(message):
    os.makedirs(".", exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")