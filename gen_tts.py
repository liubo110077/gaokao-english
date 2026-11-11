"""Generate Chinese TTS audio for 2023-甲卷-B-DIY.html.

Generates two types:
  1. Tooltip phrase explanations  → audio/2023-甲卷-B/<slug>.mp3
  2. Sentence analysis sections   → audio/2023-甲卷-B/analysis-<n>.mp3

Uses Alibaba CosyVoice-v2 (dashscope SDK).

Usage:
    python gen_tts.py               # generate all (skip existing)
    python gen_tts.py --force       # regenerate all (overwrite)
    python gen_tts.py --test        # generate only the first item
    python gen_tts.py --list        # list all items without generating
    python gen_tts.py --tips-only   # only tooltip phrases
    python gen_tts.py --analysis-only  # only sentence analyses
"""
import html, os, re, sys, time
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer

HTML_FILE = os.path.join(os.path.dirname(__file__), "2023-甲卷-B-DIY.html")
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio", "2023-甲卷-B")

dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY", "")
MODEL = "cosyvoice-v2"
VOICE = "longxiaochun_v2"


def extract_tips(html_text):
    items = []
    for m in re.finditer(r'data-tip="([^"]*)"', html_text):
        raw = html.unescape(m.group(1))
        parts = raw.split("|")
        phrase = parts[0].strip()
        explain_parts = parts[1].split("｜") if len(parts) > 1 else []
        zh_text = "。".join(p.strip() for p in explain_parts if p.strip())
        if zh_text:
            slug = re.sub(r'[^a-zA-Z0-9]+', '-', phrase.lower()).strip('-')
            items.append({"slug": slug, "text": zh_text, "label": phrase})
    return items


def extract_analyses(html_text):
    items = []
    for m in re.finditer(r'<div class="analysis" id="(analysis-\d+)">(.*?)</div>', html_text, re.DOTALL):
        aid = m.group(1)
        content = m.group(2)
        text = re.sub(r'<[^>]+>', '', content)
        text = html.unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            items.append({"slug": aid, "text": text, "label": aid})
    return items


def generate_one(item, audio_dir, force=False):
    path = os.path.join(audio_dir, f"{item['slug']}.mp3")
    if not force and os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"  skip (exists): {item['slug']}")
        return path
    start = time.time()
    synthesizer = SpeechSynthesizer(model=MODEL, voice=VOICE)
    audio = synthesizer.call(item["text"])
    elapsed = time.time() - start
    with open(path, "wb") as f:
        f.write(audio)
    size = os.path.getsize(path)
    print(f"  done: {item['slug']} ({size/1024:.1f} KB, {elapsed:.1f}s)")
    return path


def main():
    test_mode      = "--test" in sys.argv
    list_mode      = "--list" in sys.argv
    force          = "--force" in sys.argv
    tips_only      = "--tips-only" in sys.argv
    analysis_only  = "--analysis-only" in sys.argv

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html_text = f.read()

    tips     = [] if analysis_only  else extract_tips(html_text)
    analyses = [] if tips_only      else extract_analyses(html_text)
    all_items = tips + analyses

    if list_mode:
        print("── Tooltip phrases ──")
        for i, t in enumerate(tips):
            print(f"  {i+1:2d}. [{t['slug']}]  {t['text'][:60]}...")
        print(f"\n── Sentence analyses ──")
        for i, a in enumerate(analyses):
            print(f"  {i+1:2d}. [{a['slug']}]  {a['text'][:60]}...")
        print(f"\nTotal: {len(tips)} tips + {len(analyses)} analyses = {len(all_items)}")
        return

    os.makedirs(AUDIO_DIR, exist_ok=True)

    if test_mode:
        all_items = all_items[:1]
        print("Test mode: generating 1 audio file")
    else:
        print(f"Generating {len(all_items)} audio files → {AUDIO_DIR}")

    for item in all_items:
        generate_one(item, AUDIO_DIR, force=force)

    print(f"\nDone!")


if __name__ == "__main__":
    main()
