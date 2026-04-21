from config import url
import os
import time
import subprocess
from datetime import datetime

from telegram_sender import send_video

# =========================
# CONFIG
# =========================
RTSP_URL = url
OUTPUT_DIR = "recordings"

# Motion detection leggera
MOTION_WIDTH = 320
MOTION_HEIGHT = 180
MOTION_FPS = 2

PIXEL_THRESHOLD = 25
MIN_CHANGED_PIXELS = 900
SAMPLE_STEP = 4
BG_ALPHA = 0.05

# Registrazione
RECORD_SECONDS = 60

# =========================
# SETUP
# =========================
os.makedirs(OUTPUT_DIR, exist_ok=True)

FRAME_SIZE = MOTION_WIDTH * MOTION_HEIGHT


def start_motion_reader():
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-rtsp_transport", "tcp",
        "-i", RTSP_URL,
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


def start_recording():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_DIR, f"motion_{timestamp}.mp4")

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-rtsp_transport", "tcp",
        "-i", RTSP_URL,
        "-t", str(RECORD_SECONDS),
        "-c", "copy",
        "-movflags", "+faststart",
        filename
    ]

    proc = subprocess.Popen(cmd)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Registrazione avviata: {filename}")
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


def main():
    print("Sorveglianza avviata.")
    print("Termux/headless mode: niente preview grafica.")
    print("Premi Ctrl+C per uscire.\n")

    motion_proc = None
    record_proc = None
    background = None
    last_status_print = 0
    last_recorded_file = None

    try:
        motion_proc = start_motion_reader()

        while True:
            if motion_proc.poll() is not None:
                print("Reader motion interrotto. Riavvio tra 2 secondi...")
                time.sleep(2)
                motion_proc = start_motion_reader()
                background = None
                continue

            frame = read_exact(motion_proc.stdout, FRAME_SIZE)
            if frame is None:
                print("Frame non letto. Riavvio reader...")
                stop_process(motion_proc)
                time.sleep(2)
                motion_proc = start_motion_reader()
                background = None
                continue

            if background is None:
                background = bytearray(frame)
                print("Background inizializzato.")
                continue

            motion_detected, changed_pixels = detect_motion(frame, background)

            # Registrazione finita
            if record_proc is not None and record_proc.poll() is not None:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Registrazione terminata.")

                if last_recorded_file:
                    send_video(last_recorded_file)

                record_proc = None
                last_recorded_file = None

            # Movimento rilevato
            if motion_detected and record_proc is None:
                record_proc, last_recorded_file = start_recording()

            # Log
            now = time.time()
            if now - last_status_print >= 5:
                stato = "MOVIMENTO" if motion_detected else "NESSUN MOVIMENTO"
                rec = " | REC ON" if record_proc is not None else ""

                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"{stato} | changed={changed_pixels}{rec}"
                )

                last_status_print = now

    except KeyboardInterrupt:
        print("\nInterruzione richiesta. Chiusura in corso...")

    finally:
        stop_process(motion_proc)
        stop_process(record_proc)
        print("Chiuso.")


if __name__ == "__main__":
    main()