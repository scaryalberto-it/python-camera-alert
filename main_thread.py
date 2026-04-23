from config import CAMERAS
import os
import time
import subprocess
from datetime import datetime
import threading
from log_file import write_log

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
RECORD_TIMEOUT_GRACE = 15   # tolleranza extra prima di forzare la chiusura

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
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-t", str(RECORD_SECONDS),
        "-an",
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
            proc.wait(timeout=2)
        except Exception:
            pass


def run_camera(camera):
    camera_name = camera["name"]
    rtsp_url = camera["url"]

    print(f"[{camera_name}] Sorveglianza avviata.")

    motion_proc = None
    record_proc = None
    record_start_time = None
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

            # Registrazione finita normalmente
            if record_proc is not None and record_proc.poll() is not None:
                print(f"[{camera_name}] Registrazione terminata.")

                # if last_recorded_file:
                #     asyncio.run(send_video(last_recorded_file))

                record_proc = None
                record_start_time = None
                last_recorded_file = None

            # Registrazione bloccata: forzo chiusura
            if record_proc is not None and record_start_time is not None:
                elapsed = time.time() - record_start_time
                if elapsed > (RECORD_SECONDS + RECORD_TIMEOUT_GRACE):
                    print(f"[{camera_name}] Registrazione bloccata da {int(elapsed)} secondi. Forzo chiusura.")
                    stop_process(record_proc)
                    record_proc = None
                    record_start_time = None
                    last_recorded_file = None

            # Avvio nuova registrazione solo se non ce n'è una già attiva
            if motion_detected and record_proc is None:
                record_proc, last_recorded_file = start_recording(rtsp_url, camera_name)
                record_start_time = time.time()

            now = time.time()
            if now - last_status_print >= 5:

                # Segna i batti per verificare se il sistema è "vivo", scrivedno anche quela camera
                hearth_beat(camera_name)

                stato = "MOVIMENTO" if motion_detected else "nessun movimento"
                rec = " | REC ON" if record_proc is not None else ""
                ora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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


def hearth_beat(cam):
    with open("heartbeat.txt", "a", encoding="utf-8") as f:
        testo = f"{cam}__Alive: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f.write(testo)


if __name__ == "__main__":
    main()