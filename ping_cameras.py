import subprocess
from config import CAMERAS

TIMEOUT_SECONDS = 15


def check_rtsp(camera_name, rtsp_url):
    cmd = [
        "ffprobe",
        "-rtsp_transport", "tcp",
        "-v", "debug",
        "-timeout", str(TIMEOUT_SECONDS * 1000000),
        rtsp_url
    ]

    print(f"\n=== CONTROLLO RTSP: {camera_name} ===")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS + 5
        )

        output = (result.stdout or "") + "\n" + (result.stderr or "")
        out = output.lower()

        if "200 ok" in out:
            print(f"{camera_name}: RTSP OK -> 200 OK")
        elif "401" in out:
            print(f"{camera_name}: RTSP KO -> 401 Unauthorized")
        elif "404" in out:
            print(f"{camera_name}: RTSP KO -> 404 Not Found")
        elif "timeout" in out or "timed out" in out:
            print(f"{camera_name}: RTSP KO -> Timeout")
        elif result.returncode == 0:
            print(f"{camera_name}: RTSP OK -> Stream raggiungibile")
        else:
            print(f"{camera_name}: RTSP KO -> Errore generico")

    except subprocess.TimeoutExpired:
        print(f"{camera_name}: RTSP KO -> Timeout processo")
    except Exception as e:
        print(f"{camera_name}: Errore -> {e}")


def main():
    for cam in CAMERAS:
        check_rtsp(cam["name"], cam["url"])


if __name__ == "__main__":
    main()