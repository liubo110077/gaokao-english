"""Generate TTS audio using Volcano Engine seed-tts-2.0.

Generates three types:
  1. Tooltip phrase explanations (Chinese) → audio/<passage>/<slug>.mp3
  2. Sentence analysis sections  (Chinese) → audio/<passage>/analysis-<n>.mp3
  3. English word/phrase pronunciation     → audio/<passage>/en-word-<slug>.mp3

Usage:
    python volc_tts_gen.py                      # B篇 (default)
    python volc_tts_gen.py --passage A          # A篇
    python volc_tts_gen.py --passage D          # D篇
    python volc_tts_gen.py --force              # overwrite existing
    python volc_tts_gen.py --test               # one item only
    python volc_tts_gen.py --list               # list without generating
    python volc_tts_gen.py --tips-only
    python volc_tts_gen.py --analysis-only
    python volc_tts_gen.py --en-words-only      # 只生成英文单词发音
    python volc_tts_gen.py --en-words           # 同时生成英文发音（和中文一起）
"""
import asyncio, hashlib, html, json, os, re, struct, subprocess, sys, uuid

from volc_config import API_KEY, RESOURCE_ID, SPEAKER, EN_SPEAKER
SAMPLE_RATE = 24000
URL         = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"

_BASE = os.path.dirname(os.path.abspath(__file__))

PASSAGE_MAP = {
    "A": ("2023-甲卷-A-Bangkok.html",  "audio/2023-甲卷-A"),
    "B": ("2023-甲卷-B-DIY.html",      "audio/2023-甲卷-B"),
    "C": ("2023-甲卷-C-Socrates.html", "audio/2023-甲卷-C"),
    "D": ("北京卷-D-Friends.html",     "audio/北京卷-D"),
}

def _resolve_passage():
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--passage" and i < len(sys.argv):
            return sys.argv[i + 1].upper()
    return "B"

_passage = _resolve_passage()
_html_name, _audio_rel = PASSAGE_MAP[_passage]
HTML_FILE = os.path.join(_BASE, _html_name)
AUDIO_DIR = os.path.join(_BASE, _audio_rel)

E_START_CONN      = 1
E_FINISH_CONN     = 2
E_START_SESSION   = 100
E_FINISH_SESSION  = 102
E_SESSION_FINISHED = 152
E_TASK_REQUEST    = 200
E_TTS_RESPONSE    = 352
E_SENTENCE_START  = 350
E_SENTENCE_END    = 351


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


def extract_en_words(html_text):
    """Extract English tooltip phrases for pronunciation audio (en-word-*.mp3)."""
    items = []
    seen = set()
    for m in re.finditer(r'data-tip="([^"]*)"', html_text):
        raw = html.unescape(m.group(1))
        phrase = raw.split("|")[0].strip()
        if phrase and phrase not in seen:
            seen.add(phrase)
            slug = 'en-word-' + re.sub(r'[^a-zA-Z0-9]+', '-', phrase.lower()).strip('-')
            items.append({"slug": slug, "text": phrase, "label": phrase})
    return items


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
        content = re.sub(r'<button[^>]*>.*?</button>', '', m.group(2), flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '', content)
        text = html.unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            items.append({"slug": aid, "text": text, "label": aid})
    return items


def _text_hash(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _load_cache():
    path = os.path.join(AUDIO_DIR, ".tts_cache.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache):
    os.makedirs(AUDIO_DIR, exist_ok=True)
    path = os.path.join(AUDIO_DIR, ".tts_cache.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


async def synthesize_with_speaker(text, speaker):
    """Like synthesize() but with a custom speaker."""
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
            "speaker": speaker,
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


async def generate_one(item, force=False, cache=None, speaker=None):
    path = os.path.join(AUDIO_DIR, f"{item['slug']}.mp3")
    current_hash = _text_hash(item["text"])
    cached_hash = cache.get(item["slug"]) if cache is not None else None

    if not force and os.path.exists(path) and os.path.getsize(path) > 0:
        if cached_hash == current_hash:
            print(f"  skip: {item['slug']}")
            return
        print(f"  update: {item['slug']} (text changed)")

    try:
        spk = speaker or SPEAKER
        pcm = await synthesize_with_speaker(item["text"], spk)
        pcm_to_mp3(pcm, SAMPLE_RATE, path)
        if cache is not None:
            cache[item["slug"]] = current_hash
        print(f"  done: {item['slug']} ({os.path.getsize(path)/1024:.1f} KB)")
    except Exception as e:
        print(f"  FAIL: {item['slug']} — {e}")


async def main():
    test_mode     = "--test" in sys.argv
    force         = "--force" in sys.argv
    list_mode     = "--list" in sys.argv
    tips_only     = "--tips-only" in sys.argv
    analysis_only = "--analysis-only" in sys.argv
    en_words_mode = "--en-words" in sys.argv
    en_words_only = "--en-words-only" in sys.argv

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html_text = f.read()

    if en_words_only:
        zh_items = []
    else:
        tips     = [] if analysis_only else extract_tips(html_text)
        analyses = [] if tips_only     else extract_analyses(html_text)
        zh_items = tips + analyses

    en_items = extract_en_words(html_text) if (en_words_mode or en_words_only) else []

    if list_mode:
        if zh_items:
            tips_list = [] if analysis_only else extract_tips(html_text)
            an_list   = [] if tips_only     else extract_analyses(html_text)
            print("── Tooltip phrases ──")
            for t in tips_list:
                print(f"  [{t['slug']}]  {t['text'][:70]}...")
            print("\n── Sentence analyses ──")
            for a in an_list:
                print(f"  [{a['slug']}]  {a['text'][:70]}...")
        if en_items:
            print("\n── English words ──")
            for e in en_items:
                print(f"  [{e['slug']}]  {e['text']}")
        print(f"\nTotal: {len(zh_items)} ZH + {len(en_items)} EN")
        return

    os.makedirs(AUDIO_DIR, exist_ok=True)
    cache = _load_cache()

    all_count = len(zh_items) + len(en_items)
    if test_mode:
        zh_items = zh_items[:1] if zh_items else []
        en_items = en_items[:1] if en_items else []
        print("Test mode: up to 1 item per type")
    else:
        print(f"Generating {all_count} items → {AUDIO_DIR}")

    for item in zh_items:
        await generate_one(item, force=force, cache=cache, speaker=SPEAKER)

    for item in en_items:
        await generate_one(item, force=force, cache=cache, speaker=EN_SPEAKER)

    _save_cache(cache)
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
