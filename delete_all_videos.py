import subprocess

confirm = input("Vuoi cancellare tutti i video da recordings? (yes/no): ")

if confirm.lower() == "yes":
    subprocess.run(["rm", "-f", "recordings/*"], shell=True)
    print("Video cancellati.")
else:
    print("Operazione annullata.")