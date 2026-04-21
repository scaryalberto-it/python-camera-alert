import subprocess
import sys

p1 = subprocess.Popen([sys.executable, "main_thread.py"])
p2 = subprocess.Popen([sys.executable, "stato_risorse.py"])

try:
    p1.wait()
    p2.wait()
except KeyboardInterrupt:
    p1.terminate()
    p2.terminate()
    print("Processi fermati.")