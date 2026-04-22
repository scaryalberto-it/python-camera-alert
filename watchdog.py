import os
import time
import sys
import subprocess
from datetime import datetime
from telegram_sender import send_message
import asyncio

HEARTBEAT_FILE = "heartbeat.txt"
TARGET_SCRIPT = "main.py"

CHECK_EVERY_SECONDS = 1800   # 30 minuti
MAX_AGE_SECONDS = 1800       # 30 minuti


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


def heartbeat_too_old():
    if not os.path.exists(HEARTBEAT_FILE):
        log("heartbeat.txt non trovato")
        return True

    try:
        with open(HEARTBEAT_FILE, "r", encoding="utf-8") as f:
            righe = f.readlines()

        if not righe:
            log("heartbeat vuoto")
            os.remove(HEARTBEAT_FILE)
            return True

        ultima_riga = righe[-1].strip()
        # formato: Alive: 2026-04-22 12:30:00
        data_txt = ultima_riga.replace("Alive: ", "")
        dt = datetime.strptime(data_txt, "%Y-%m-%d %H:%M:%S")

        age = (datetime.now() - dt).total_seconds()
        log(f"Età heartbeat: {int(age)} secondi")

        os.remove(HEARTBEAT_FILE)

        return age > MAX_AGE_SECONDS

    except Exception as e:
        log(f"Errore heartbeat: {e}")
        return True

def main():
    log("Watchdog avviato")
    proc = start_main()

    while True:
        time.sleep(CHECK_EVERY_SECONDS)

        if proc.poll() is not None:
            log(f"{TARGET_SCRIPT} risulta chiuso. Riavvio...")
            proc = start_main()
            continue

        # Se non vengono letti battiti da 30 minuti, manda un messaggio su telegram e riavvia tutto
        if heartbeat_too_old():
            log("Heartbeat troppo vecchio. Riavvio tutto...")
            asyncio.run(send_message("Watchdog: heartbeat non rilevato o troppo vecchio. Riavvio main.py"))
            kill_main_tree(proc)
            time.sleep(3)
            proc = start_main()
        else:
            log("Heartbeat OK")


if __name__ == "__main__":
    main()