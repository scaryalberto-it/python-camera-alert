# logger_txt.py

import sys
import traceback
from datetime import datetime

from datetime import datetime
import os

LOG_FILE = "system_log.txt"


def write_log(message):
    os.makedirs(".", exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def handle_exception(exc_type, exc_value, exc_traceback):
    """
    funzione che parte all'avvio del sistema
    :param exc_type:
    :param exc_value:
    :param exc_traceback:
    :return:
    """
    errore = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    write_log("ERRORE NON GESTITO:\n" + errore)

sys.excepthook = handle_exception