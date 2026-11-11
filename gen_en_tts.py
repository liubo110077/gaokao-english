"""Generate English TTS audio for b-passage.html sentences.

Uses ElevenLabs API, Daniel voice (British male, authoritative).

Usage:
    python gen_en_tts.py               # generate all (skip existing)
    python gen_en_tts.py --force       # regenerate all
    python gen_en_tts.py --test        # first sentence only
"""
import os, sys, time
from elevenlabs.client import ElevenLabs

HTML_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(HTML_DIR, "audio")

API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID = "onwK4e9ZLuTAKqWW03F9"  # Daniel - British male
MODEL_ID = "eleven_v4"
OUTPUT_FORMAT = "mp3_44100_128"

SENTENCES = [
    "Terri Bolton is a dab hand when it comes to DIY.",
    "Skilled at putting up shelves and piecing together furniture, she never pays someone else to do a job she can do herself.",
    "She credits these skills to her late grandfather and builder Derek Lloyd.",
    "From the age of six, Terri, now 26, accompanied Derek to work during her school holidays.",
    "A day's work was rewarded with five pounds in pocket money.",
    "She says: I'm sure I wasn't much of a help to start with, painting the rooms and putting down the flooring throughout the house.",
    "It took weeks and was backbreaking work, but I know he was proud of my skills.",
    "Terri, who now rents a house with friends in Wandsworth, South West London, says DIY also saves her from losing any deposit when a tenancy comes to an end.",
    "She adds: I've moved house many times and I always like to personalise my room and put up pictures.",
    "So, it's been useful to know how to cover up holes and repaint a room to avoid any charges when I've moved out.",
    "With millions of people likely to take on DIY projects over the coming weeks, new research shows that more than half of people are planning to make the most of the long, warm summer days to get jobs done.",
    "The average spend per project will be around eight hundred and twenty three pounds.",
    "Two thirds of people aim to improve their comfort while at home.",
    "A fifth wish to increase the value of their house.",
    "Though DIY has traditionally been seen as a male hobby, the research shows it is women now leading the charge.",
]


def main():
    test_mode = "--test" in sys.argv
    force = "--force" in sys.argv

    client = ElevenLabs(api_key=API_KEY)
    os.makedirs(AUDIO_DIR, exist_ok=True)

    items = SENTENCES[:1] if test_mode else SENTENCES
    print(f"Generating {len(items)} English audio files (Daniel)...")

    for i, text in enumerate(items):
        path = os.path.join(AUDIO_DIR, f"en-s{i:02d}.mp3")
        if not force and os.path.exists(path) and os.path.getsize(path) > 0:
            print(f"  [{i+1}/{len(items)}] skip: en-s{i:02d}")
            continue
        start = time.time()
        audio = client.text_to_speech.convert(
            text=text, voice_id=VOICE_ID, model_id=MODEL_ID,
            output_format=OUTPUT_FORMAT,
        )
        with open(path, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        elapsed = time.time() - start
        size = os.path.getsize(path)
        print(f"  [{i+1}/{len(items)}] done: en-s{i:02d} ({size/1024:.0f}KB, {elapsed:.1f}s)")

    print("Done!")


if __name__ == "__main__":
    main()
