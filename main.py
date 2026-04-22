import subprocess
import sys

p1 = subprocess.Popen([sys.executable, "main_thread.py"])
p2 = subprocess.Popen([sys.executable, "stato_risorse.py"])
p3 = subprocess.Popen([sys.executable, "resend_old_video.py"])
p4 = subprocess.Popen([sys.executable, "log_file.py"])
p5 = subprocess.Popen([sys.executable, "ping_cameras.py"])


try:
    p1.wait()
    p2.wait()
    p3.wait()
    p4.wait()
    p5.wait()

except KeyboardInterrupt:
    p1.terminate()
    p2.terminate()
    p3.terminate()
    p4.terminate()
    p5.terminate()
    print("Processi fermati.")