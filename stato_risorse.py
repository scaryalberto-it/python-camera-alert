import time
import shutil
import subprocess
from datetime import datetime

CHECK_EVERY_SECONDS = 2 * 60 * 60   # 2 ore


def get_speedtest():
    """
    Usa speedtest-cli se installato.
    """
    if shutil.which("speedtest") is None and shutil.which("speedtest-cli") is None:
        return "Speedtest non installato"

    cmd = ["speedtest-cli", "--simple"]
    if shutil.which("speedtest"):
        cmd = ["speedtest"]

    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=180)
        return out.strip()
    except Exception as e:
        return f"Errore speedtest: {e}"


def get_resources():
    """
    Legge stato CPU/RAM/Storage da Android/Linux.
    """
    try:
        mem = subprocess.check_output(["free", "-m"], text=True)
    except:
        mem = "free non disponibile"

    try:
        disk = subprocess.check_output(["df", "-h", "/"], text=True)
    except:
        disk = "df non disponibile"

    try:
        uptime = subprocess.check_output(["uptime"], text=True)
    except:
        uptime = "uptime non disponibile"

    return f"""
===== RISORSE =====
{uptime}

===== RAM =====
{mem}

===== DISK =====
{disk}
"""


def main():
    print("Monitor avviato. Controllo ogni 2 ore...\n")

    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("=" * 60)
        print(f"[{now}] CHECK SISTEMA")
        print("=" * 60)

        print(get_resources())
        print("===== SPEEDTEST =====")
        print(get_speedtest())
        print("\n")

        time.sleep(CHECK_EVERY_SECONDS)


if __name__ == "__main__":
    main()