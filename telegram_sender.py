from config import BOT_TOKEN, CHAT_ID
import asyncio
from telegram import Bot
import subprocess
import os

# Manda messaggio testuale su telegram (es. await send_message("Test messaggio")
async def send_message(text):
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(
        chat_id=CHAT_ID,
        text=text
    )

# Manda video su telegram (es. await send_video("recordings/test.mp4")
async def send_video(video_path):
    bot = Bot(token=BOT_TOKEN)

    video_path = comprimi_video(video_path)

    with open(video_path, "rb") as f:
        await bot.send_video(
            chat_id=CHAT_ID,
            video=f
        )

# esempi uso
async def main():
    #await send_message("Test messaggio")
    await send_video("recordings/test.mp4")

def comprimi_video(input_path):
    """
    Prende il path di un video e crea una versione compressa.
    Ritorna il path del file compresso.
    Richiede ffmpeg installato.
    """

    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_compressed.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-vf", "scale=1280:-2",
        "-r", "15",
        "-c:v", "libx264",
        "-crf", "30",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "96k",
        output_path
    ]

    subprocess.run(cmd, check=True)
    return output_path

# scommentare per testare invio messaggi
asyncio.run(main())