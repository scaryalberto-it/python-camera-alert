import os
import time
import asyncio
from datetime import datetime

from telegram_sender import send_video

RECORDINGS_DIR = "recordings"
CHECK_EVERY_SECONDS = 300       # ogni 5 minuti
MIN_FILE_AGE_SECONDS = 600      # solo file più vecchi di 10 minuti


def is_old_enough(filepath):
    try:
        file_mtime = os.path.getmtime(filepath)
        age_seconds = time.time() - file_mtime
        return age_seconds >= MIN_FILE_AGE_SECONDS
    except Exception:
        return False


def get_old_mp4_files():
    if not os.path.exists(RECORDINGS_DIR):
        return []

    files = []

    for name in os.listdir(RECORDINGS_DIR):
        if not name.lower().endswith(".mp4"):
            continue

        filepath = os.path.join(RECORDINGS_DIR, name)

        if not os.path.isfile(filepath):
            continue

        if not is_old_enough(filepath):
            continue

        files.append(filepath)

    files.sort(key=os.path.getmtime)
    return files


def retry_send():
    print("Retry sender avviato.")
    print("Controllo file vecchi di almeno 10 minuti.\n")

    while True:
        files = get_old_mp4_files()

        if files:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Trovati {len(files)} file da recuperare.")

        for filepath in files:
            try:
                print(f"Tento invio: {filepath}")
                asyncio.run(send_video(filepath))
                print(f"Inviato con successo: {filepath}")
            except Exception as e:
                print(f"Errore invio {filepath}: {e}")

        time.sleep(CHECK_EVERY_SECONDS)
