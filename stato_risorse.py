import time
import shutil
import subprocess
import asyncio
from datetime import datetime

from telegram_sender import send_message
from config import CAMERAS

REPORT_EVERY_SECONDS = 2 * 60 * 60   # 2 ore
CAMERA_CHECK_EVERY_SECONDS = 300       # 5 minuto

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
        mem = "free non disponibile"

    try:
        disk = subprocess.check_output(["df", "-h", "/"], text=True)
    except Exception:
        disk = "df non disponibile"

    try:
        uptime = subprocess.check_output(["uptime"], text=True)
    except Exception:
        uptime = "uptime non disponibile"

    return f"""
===== RISORSE =====
{uptime}

===== RAM =====
{mem}

===== DISK =====
{disk}
"""


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
    rows.append("===== SALUTE TELECAMERE =====")

    for idx, (camera_name, fail_count) in enumerate(ranking, start=1):
        ok_count = camera_ok_stats.get(camera_name, 0)
        total = ok_count + fail_count
        rows.append(
            f"{idx}. {camera_name} -> fail: {fail_count} | ok: {ok_count} | check totali: {total}"
        )

    return "\n".join(rows)


def main():
    global last_camera_check, last_report_time

    print("Monitor avviato.")
    print("Check telecamere ogni 1 minuto.")
    print("Report Telegram ogni 2 ore.\n")

    while True:
        now_ts = time.time()

        if now_ts - last_camera_check >= CAMERA_CHECK_EVERY_SECONDS:
            update_camera_health()
            last_camera_check = now_ts
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Check telecamere eseguito.")

        if last_report_time == 0 or now_ts - last_report_time >= REPORT_EVERY_SECONDS:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            resources = get_resources()
            speedtest = get_speedtest()
            camera_health = get_camera_health_report()

            msg = f"""[{now_str}] CHECK SISTEMA

{resources}

===== SPEEDTEST =====
{speedtest}

{camera_health}
"""

            asyncio.run(send_message(msg))
            last_report_time = now_ts
            print(f"[{now_str}] Report Telegram inviato.")

        time.sleep(5)


if __name__ == "__main__":
    main()