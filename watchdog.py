import os
import time
import sys
import subprocess
from datetime import datetime
from telegram_sender import send_message
import asyncio

HEARTBEAT_FILE = "heartbeat.txt"
TARGET_SCRIPT = "main.py"

CHECK_EVERY_SECONDS = 300   # 5 minuti
MAX_AGE_SECONDS = 600       # 10 minuti


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def start_main():
    proc = subprocess.Popen([sys.executable, TARGET_SCRIPT])
    log(f"Avviato {TARGET_SCRIPT} con PID {proc.pid}")
    return proc


def kill_main_tree(proc):
    if proc.poll() is None:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                text=True
            )
            log(f"Terminato {TARGET_SCRIPT} con PID {proc.pid}")
        except Exception as e:
            log(f"Errore kill: {e}")
    else:
        log(f"{TARGET_SCRIPT} già terminato")


def main():
    log("Watchdog avviato")
    proc = start_main()

    while True:
        time.sleep(CHECK_EVERY_SECONDS)

        if proc.poll() is not None:
            log(f"{TARGET_SCRIPT} risulta chiuso. Riavvio...")
            proc = start_main()
            continue

        # Se non vengono letti battiti da 30 minuti o una camera non è raggingibile da 10, manda un messaggio su telegram e riavvia tutto
        if cameras_down():
            log("Heartbeat troppo vecchio. Riavvio tutto...")
            asyncio.run(send_message("Watchdog: heartbeat non rilevato o troppo vecchio. Riavvio main.py"))
            kill_main_tree(proc)
            time.sleep(3)
            proc = start_main()

        else:
            log("Heartbeat OK")

from config import CAMERAS
from datetime import datetime
import os

def cameras_down():
    file_name = "heartbeat.txt"

    if not os.path.exists(file_name):
        return True

    try:
        with open(file_name, "r", encoding="utf-8") as f:
            righe = f.readlines()

        if not righe:
            return True

        ultimi_log = {}

        for riga in righe:
            riga = riga.strip()

            if "__" not in riga:
                continue

            nome_cam, ts = riga.split("__", 1)

            ts = ts.replace("Alive: ", "").strip()

            ultimi_log[nome_cam] = ts

        for camera in CAMERAS:
            nome = camera["name"]

            if nome not in ultimi_log:
                return True

            dt = datetime.strptime(ultimi_log[nome], "%Y-%m-%d %H:%M:%S")
            age = (datetime.now() - dt).total_seconds()

            if age > 600:
                return True

        return False

    except:
        return True

if __name__ == "__main__":
    main()