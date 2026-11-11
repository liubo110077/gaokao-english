"""Generate English pronunciation audio for vocab words using Volcano Engine seed-tts-2.0.

Usage:
    python gen_en_pronunciation.py          # generate all (skip existing)
    python gen_en_pronunciation.py --force  # overwrite existing
    python gen_en_pronunciation.py --test   # one item only
    python gen_en_pronunciation.py --list   # list without generating
"""
import asyncio, hashlib, html, json, os, re, struct, subprocess, sys, uuid

from volc_config import API_KEY  # read from env VOLC_API_KEY or .env (not committed)
RESOURCE_ID = "seed-tts-2.0"
SPEAKER     = "zh_male_shaonianzixin_uranus_bigtts"
SAMPLE_RATE = 24000
URL         = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"

HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "2023-甲卷-B-DIY.html")
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio", "2023-甲卷-B")

E_START_CONN      = 1
E_FINISH_CONN     = 2
E_START_SESSION   = 100
E_FINISH_SESSION  = 102
E_SESSION_FINISHED = 152
E_TASK_REQUEST    = 200
E_TTS_RESPONSE    = 352


def frame(event, payload=b"{}", session_id=""):
    data = b"\x11\x14\x10\x00" + struct.pack(">i", event)
    if session_id:
        sid = session_id.encode()
        data += struct.pack(">I", len(sid)) + sid
    return data + struct.pack(">I", len(payload)) + payload


def parse_frame(data):
    if not isinstance(data, bytes) or len(data) < 4 or data[0] != 0x11:
        raise RuntimeError("Invalid frame header")
    msg_type = data[1] >> 4
    pos = 4

    def read_int():
        nonlocal pos
        v = struct.unpack_from(">I", data, pos)[0]; pos += 4; return v

    def read_field():
        nonlocal pos
        size = read_int(); val = data[pos:pos + size]; pos += size; return val

    if msg_type == 0xF:
        code = read_int(); read_field()
        raise RuntimeError(f"TTS error code={code}")

    event = read_int()
    fields = []
    while pos < len(data):
        fields.append(read_field())
    payload = fields[-1] if fields else b""
    return msg_type, event, payload


def pcm_to_mp3(pcm_data, sample_rate, out_path):
    proc = subprocess.run(
        ["ffmpeg", "-y", "-f", "s16le", "-ar", str(sample_rate), "-ac", "1",
         "-i", "pipe:0", "-codec:a", "libmp3lame", "-q:a", "2", out_path],
        input=pcm_data, capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.decode()[:200]}")


async def synthesize(text):
    from websockets.legacy.client import connect

    session_id = str(uuid.uuid4())
    headers = {
        "X-Api-Key": API_KEY,
        "X-Api-Resource-Id": RESOURCE_ID,
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }
    ws = await connect(URL, extra_headers=headers, max_size=10*1024*1024,
                       max_queue=16, open_timeout=10, close_timeout=5)
    try:
        await ws.send(frame(E_START_CONN))
        parse_frame(await ws.recv())

        start_payload = json.dumps({"req_params": {
            "speaker": SPEAKER,
            "audio_params": {"format": "pcm", "sample_rate": SAMPLE_RATE},
        }}).encode()
        await ws.send(frame(E_START_SESSION, start_payload, session_id))
        parse_frame(await ws.recv())

        text_payload = json.dumps({"req_params": {"text": text}}).encode()
        await ws.send(frame(E_TASK_REQUEST, text_payload, session_id))
        await ws.send(frame(E_FINISH_SESSION, session_id=session_id))

        pcm_chunks = []
        while True:
            msg_type, event, payload = parse_frame(await ws.recv())
            if msg_type == 0xB and event == E_TTS_RESPONSE:
                pcm_chunks.append(payload)
            elif event == E_SESSION_FINISHED:
                break
        await ws.send(frame(E_FINISH_CONN))
        parse_frame(await ws.recv())
    finally:
        await ws.close()
    return b"".join(pcm_chunks)


def extract_vocab_words(html_text):
    """Extract all English words/phrases from speakWord() calls and data-tip attributes."""
    items = []
    seen = set()
    for m in re.finditer(r"speakWord\('([^']+)'\)", html_text):
        word = m.group(1)
        if word not in seen and '${' not in word:
            seen.add(word)
            slug = "en-word-" + re.sub(r'[^a-zA-Z0-9]+', '-', word.lower()).strip('-')
            items.append({"slug": slug, "word": word})
    for m in re.finditer(r'data-tip="([^"|]+)', html_text):
        phrase = html.unescape(m.group(1)).strip()
        phrase_clean = re.sub(r'\.\.\.', ' ', phrase).strip()
        if phrase_clean not in seen:
            seen.add(phrase_clean)
            slug = "en-word-" + re.sub(r'[^a-zA-Z0-9]+', '-', phrase_clean.lower()).strip('-')
            items.append({"slug": slug, "word": phrase_clean})
    return items


def _text_hash(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _load_cache():
    path = os.path.join(AUDIO_DIR, ".en_cache.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache):
    os.makedirs(AUDIO_DIR, exist_ok=True)
    path = os.path.join(AUDIO_DIR, ".en_cache.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


async def generate_one(item, force=False, cache=None):
    path = os.path.join(AUDIO_DIR, f"{item['slug']}.mp3")
    current_hash = _text_hash(item["word"])
    cached_hash = cache.get(item["slug"]) if cache is not None else None

    if not force and os.path.exists(path) and os.path.getsize(path) > 0:
        if cached_hash == current_hash:
            print(f"  skip: {item['slug']}")
            return
        print(f"  update: {item['slug']} (word changed)")

    try:
        pcm = await synthesize(item["word"])
        pcm_to_mp3(pcm, SAMPLE_RATE, path)
        if cache is not None:
            cache[item["slug"]] = current_hash
        print(f"  done: {item['slug']} ({os.path.getsize(path)/1024:.1f} KB)")
    except Exception as e:
        print(f"  FAIL: {item['slug']} — {e}")


async def main():
    test_mode = "--test" in sys.argv
    force     = "--force" in sys.argv
    list_mode = "--list" in sys.argv

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html_text = f.read()

    items = extract_vocab_words(html_text)

    if list_mode:
        print("── Vocab words ──")
        for t in items:
            print(f"  [{t['slug']}]  {t['word']}")
        print(f"\nTotal: {len(items)} words")
        return

    os.makedirs(AUDIO_DIR, exist_ok=True)
    cache = _load_cache()

    if test_mode:
        items = items[:1]
        print("Test mode: 1 item")
    else:
        print(f"Generating {len(items)} items → {AUDIO_DIR}")

    for item in items:
        await generate_one(item, force=force, cache=cache)

    _save_cache(cache)
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
