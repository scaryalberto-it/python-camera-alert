from config import CAMERAS
import os
import time
import subprocess
from datetime import datetime
import asyncio
import threading
from log_file import write_log
from telegram_sender import send_video

# =========================
# CONFIG
# =========================
OUTPUT_DIR = "recordings"

# Motion detection leggera
MOTION_WIDTH = 320
MOTION_HEIGHT = 180
MOTION_FPS = 2

PIXEL_THRESHOLD = 25
MIN_CHANGED_PIXELS = 400
SAMPLE_STEP = 4
BG_ALPHA = 0.05

# Registrazione
RECORD_SECONDS = 60

# =========================
# SETUP
# =========================
os.makedirs(OUTPUT_DIR, exist_ok=True)

FRAME_SIZE = MOTION_WIDTH * MOTION_HEIGHT


def start_motion_reader(rtsp_url):
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-vf", f"fps={MOTION_FPS},scale={MOTION_WIDTH}:{MOTION_HEIGHT},format=gray",
        "-an",
        "-sn",
        "-dn",
        "-f", "rawvideo",
        "-pix_fmt", "gray",
        "-"
    ]

    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=10**7
    )


def read_exact(pipe, size):
    data = b""
    while len(data) < size:
        chunk = pipe.read(size - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def detect_motion(frame_bytes, background):
    changed = 0

    for i in range(0, FRAME_SIZE, SAMPLE_STEP):
        cur = frame_bytes[i]
        bg = background[i]

        if abs(cur - bg) > PIXEL_THRESHOLD:
            changed += 1

        background[i] = int(bg * (1.0 - BG_ALPHA) + cur * BG_ALPHA)

    return changed >= MIN_CHANGED_PIXELS, changed


def start_recording(rtsp_url, camera_name):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_DIR, f"{camera_name}_{timestamp}.mp4")

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-t", str(RECORD_SECONDS),
        "-c", "copy",
        "-movflags", "+faststart",
        filename
    ]

    proc = subprocess.Popen(cmd)
    print(f"[{camera_name}] Registrazione avviata: {filename}")
    return proc, filename


def stop_process(proc):
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_camera(camera):
    camera_name = camera["name"]
    rtsp_url = camera["url"]

    print(f"[{camera_name}] Sorveglianza avviata.")

    motion_proc = None
    record_proc = None
    background = None
    last_status_print = 0
    last_recorded_file = None

    try:
        motion_proc = start_motion_reader(rtsp_url)

        while True:
            if motion_proc.poll() is not None:
                print(f"[{camera_name}] Reader interrotto. Riavvio...")
                time.sleep(2)
                motion_proc = start_motion_reader(rtsp_url)
                background = None
                continue

            frame = read_exact(motion_proc.stdout, FRAME_SIZE)

            if frame is None:
                print(f"[{camera_name}] Frame non letto. Riavvio...")
                stop_process(motion_proc)
                time.sleep(2)
                motion_proc = start_motion_reader(rtsp_url)
                background = None
                continue

            if background is None:
                background = bytearray(frame)
                print(f"[{camera_name}] Background inizializzato.")
                continue

            motion_detected, changed_pixels = detect_motion(frame, background)

            if record_proc is not None and record_proc.poll() is not None:
                print(f"[{camera_name}] Registrazione terminata.")

                if last_recorded_file:
                    asyncio.run(send_video(last_recorded_file))

                record_proc = None
                last_recorded_file = None

            if motion_detected and record_proc is None:
                record_proc, last_recorded_file = start_recording(rtsp_url, camera_name)

            now = time.time()
            if now - last_status_print >= 5:

                # Registra il buon funzionamento dei thread
                hearth_beat()

                stato = "MOVIMENTO" if motion_detected else "nessun movimento"
                rec = " | REC ON" if record_proc is not None else ""
                ora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # stampa il log nel terminale solo se vede un movimento
                print(f"[{camera_name}] {stato} | pixel_changed={changed_pixels}{rec} | {ora}")

                if motion_detected:
                    write_log(f"{ora} | [{camera_name}] Movimento rilevato")

                last_status_print = now

    except KeyboardInterrupt:
        pass

    finally:
        stop_process(motion_proc)
        stop_process(record_proc)


def main():
    print("Sistema multi-camera avviato.\n")

    threads = []

    for camera in CAMERAS:
        t = threading.Thread(target=run_camera, args=(camera,), daemon=True)
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nChiusura in corso...")


def hearth_beat():
    with open("heartbeat.txt", "a", encoding="utf-8") as f:
        testo = f"Alive: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f.write(testo)

if __name__ == "__main__":
    main()