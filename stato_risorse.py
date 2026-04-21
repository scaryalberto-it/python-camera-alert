import time
import shutil
import subprocess
import asyncio
from datetime import datetime

from telegram_sender import send_message
from config import CAMERAS

from info_server import count_recordings

REPORT_EVERY_SECONDS = 2 * 60 * 60   # 2 ore
CAMERA_CHECK_EVERY_SECONDS = 300     # 5 minuti

camera_fail_stats = {camera["name"]: 0 for camera in CAMERAS}
camera_ok_stats = {camera["name"]: 0 for camera in CAMERAS}
last_camera_check = 0
last_report_time = 0


def get_speedtest():
    if shutil.which("speedtest") is None and shutil.which("speedtest-cli") is None:
        return "Speedtest non installato"

    cmd = ["speedtest-cli", "--simple"]
    if shutil.which("speedtest"):
        cmd = ["speedtest"]

    try:
        out = subprocess.check_output(
            cmd,
            text=True,
            stderr=subprocess.STDOUT,
            timeout=180
        )
        return out.strip()
    except Exception as e:
        return f"Errore speedtest: {e}"


def get_resources():
    try:
        mem = subprocess.check_output(["free", "-m"], text=True)
    except Exception:
        mem = None

    try:
        disk = subprocess.check_output(["df", "-h", "/"], text=True)
    except Exception:
        disk = None

    try:
        uptime = subprocess.check_output(["uptime"], text=True)
    except Exception:
        uptime = None

    return uptime, mem, disk


def extract_ram_info(mem_text):
    if not mem_text:
        return "RAM non disponibile"

    try:
        lines = mem_text.strip().splitlines()
        parts = lines[1].split()
        total = parts[1]
        used = parts[2]
        free = parts[3]
        return f"RAM: {used} MB usati su {total} MB, liberi {free} MB"
    except Exception:
        return "RAM non disponibile"


def extract_disk_info(disk_text):
    if not disk_text:
        return "Disco non disponibile"

    try:
        lines = disk_text.strip().splitlines()
        parts = lines[1].split()
        total = parts[1]
        used = parts[2]
        free = parts[3]
        usage = parts[4]
        return f"Disco: {used} usati su {total}, liberi {free} ({usage} occupato)"
    except Exception:
        return "Disco non disponibile"


def extract_uptime_info(uptime_text):
    if not uptime_text:
        return "Uptime non disponibile"

    try:
        return f"Uptime: {uptime_text.strip()}"
    except Exception:
        return "Uptime non disponibile"


def format_speedtest(speedtest_text):
    if not speedtest_text:
        return "Speedtest non disponibile"

    if "Errore" in speedtest_text or "non installato" in speedtest_text:
        return speedtest_text

    return speedtest_text.strip()


def check_camera_rtsp(rtsp_url):
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-rtsp_transport", "tcp",
        "-stimeout", "5000000",
        "-i", rtsp_url,
        "-frames:v", "1",
        "-f", "null",
        "-"
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15
        )
        return result.returncode == 0
    except Exception:
        return False


def update_camera_health():
    for camera in CAMERAS:
        camera_name = camera["name"]
        rtsp_url = camera["url"]

        ok = check_camera_rtsp(rtsp_url)

        if ok:
            camera_ok_stats[camera_name] += 1
        else:
            camera_fail_stats[camera_name] += 1


def get_camera_health_report():
    ranking = sorted(
        camera_fail_stats.items(),
        key=lambda x: x[1],
        reverse=True
    )

    rows = []
    rows.append("Salute telecamere:")

    for idx, (camera_name, fail_count) in enumerate(ranking, start=1):
        ok_count = camera_ok_stats.get(camera_name, 0)
        total = ok_count + fail_count

        if fail_count == 0:
            stato = "stabile"
        elif fail_count <= 2:
            stato = "qualche errore"
        else:
            stato = "instabile"

        rows.append(
            f"{idx}. {camera_name}: {stato} | errori {fail_count}, controlli ok {ok_count}, totale check {total}"
        )

    return "\n".join(rows)


def build_natural_message():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    uptime_text, mem_text, disk_text = get_resources()
    speedtest = get_speedtest()
    camera_health = get_camera_health_report()

    uptime_info = extract_uptime_info(uptime_text)
    ram_info = extract_ram_info(mem_text)
    disk_info = extract_disk_info(disk_text)
    speedtest_info = format_speedtest(speedtest)

    msg = (
        f"Report sistema delle {now_str}\n\n"
        f"{uptime_info}\n"
        f"{ram_info}\n"
        f"{disk_info}\n\n"
        f"Connessione:\n{speedtest_info}\n\n"
        f"{camera_health}\n"
        f"Numero di file in recordings: {count_recordings()}\n"
    )

    return msg


def main():
    global last_camera_check, last_report_time

    print("Monitor avviato.")
    print("Check telecamere ogni 5 minuti.")
    print("Report Telegram ogni 2 ore.\n")

    while True:
        now_ts = time.time()

        if now_ts - last_camera_check >= CAMERA_CHECK_EVERY_SECONDS:
            update_camera_health()
            last_camera_check = now_ts
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Check telecamere eseguito.")

        if last_report_time == 0 or now_ts - last_report_time >= REPORT_EVERY_SECONDS:
            msg = build_natural_message()

            asyncio.run(send_message(msg))
            last_report_time = now_ts
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Report Telegram inviato.")

        time.sleep(5)


if __name__ == "__main__":
    main()