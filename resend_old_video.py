import os
import time
import asyncio
from datetime import datetime

from telegram_sender import send_video

RECORDINGS_DIR = "recordings"
CHECK_EVERY_SECONDS = 300
MIN_FILE_AGE_SECONDS = 600          # 10 minuti
DELETE_AFTER_SECONDS = 3 * 24 * 60 * 60   # 3 giorni


def file_age_seconds(filepath):
    try:
        return time.time() - os.path.getmtime(filepath)
    except Exception:
        return 0


def is_old_enough(filepath):
    return file_age_seconds(filepath) >= MIN_FILE_AGE_SECONDS


def is_too_old(filepath):
    return file_age_seconds(filepath) >= DELETE_AFTER_SECONDS


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

        # se troppo vecchio cancella subito
        if is_too_old(filepath):
            try:
                os.remove(filepath)
                print(f"Cancellato file vecchio: {filepath}")
            except Exception as e:
                print(f"Errore cancellazione {filepath}: {e}")
            continue

        if is_old_enough(filepath):
            files.append(filepath)

    files.sort(key=os.path.getmtime)
    return files


def main():
    print("Retry sender avviato.")

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


if __name__ == "__main__":
    main()