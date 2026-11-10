import sys, os, re, json, html, base64, uuid, hashlib, urllib.request, concurrent.futures as cf
# usage: gen_audio.py REPO HTML_FILE AUDIO_SUBDIR [--en-only]
REPO, HTML_NAME, SUB = sys.argv[1:4]
EN_ONLY = "--en-only" in sys.argv
HTML = os.path.join(REPO, HTML_NAME)
OUT = os.path.join(REPO, "audio", SUB)
os.makedirs(OUT, exist_ok=True)
KEY = dict(l.strip().split("=", 1) for l in open(os.path.expanduser("~/.volc_tts.env")) if "=" in l)["VOLC_API_KEY"]
SPEAKER = "zh_male_shaonianzixin_uranus_bigtts"
URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
src = open(HTML, encoding="utf-8").read()

def tts(text):
    body = json.dumps({"req_params": {"text": text, "speaker": SPEAKER,
        "audio_params": {"format": "mp3", "sample_rate": 24000}}}).encode()
    req = urllib.request.Request(URL, body, {"X-Api-Key": KEY, "X-Api-Resource-Id": "seed-tts-2.0",
        "X-Api-Request-Id": str(uuid.uuid4()), "Content-Type": "application/json"})
    audio = b""
    with urllib.request.urlopen(req, timeout=90) as r:
        for line in r:
            line = line.strip()
            if not line: continue
            d = json.loads(line)
            if d.get("code", 0) not in (0, 20000000): raise RuntimeError(d)
            if d.get("data"): audio += base64.b64decode(d["data"])
    if not audio: raise RuntimeError("empty")
    return audio

items = {}  # filename -> text
sents = json.loads(re.search(r"const sentences = (\[.*?\]);", src, re.S).group(1))
for i, s in enumerate(sents): items[f"en-s{i:02d}"] = s
words = set(re.findall(r"speakWord\('([^'$]+)'\)", src))
tips = []
for m in re.finditer(r'data-tip="([^"]*)"', src):
    parts = html.unescape(m.group(1)).split("|")
    ph = parts[0].strip(); words.add(ph)
    zh = "。".join(p.strip() for p in (parts[1].split("｜") if len(parts) > 1 else []) if p.strip())
    if zh: items[slug(ph)] = zh; tips.append(slug(ph))
for w in words: items["en-word-" + slug(w)] = w
for m in re.finditer(r'<div class="analysis" id="(analysis-\d+)">(.*?)</div>', src, re.S):
    t = re.sub(r"<button[^>]*>.*?</button>", "", m.group(2), flags=re.S)
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t))).strip()
    if t: items[m.group(1)] = t

if EN_ONLY:
    items = {k: v for k, v in items.items() if k.startswith("en-")}
cpath = os.path.join(OUT, ".tts_cache.json")
cache = json.load(open(cpath)) if os.path.exists(cpath) else {}
def job(k):
    p = os.path.join(OUT, k + ".mp3"); h = hashlib.md5(items[k].encode()).hexdigest()
    if os.path.exists(p) and cache.get(k) == h: return k, "skip"
    for _ in range(3):
        try:
            open(p, "wb").write(tts(items[k])); cache[k] = h; return k, "ok"
        except Exception as e: err = e
    return k, f"FAIL {err}"
print(len(items), "items")
with cf.ThreadPoolExecutor(4) as ex:
    res = list(ex.map(job, items))
json.dump(cache, open(cpath, "w"), ensure_ascii=False, indent=2)
print({s: sum(1 for _, r in res if r.startswith(s)) for s in ("ok", "skip", "FAIL")})
for k, r in res:
    if r.startswith("FAIL"): print(k, r)
# print ZH_AUDIO map for tips + analyses
zh = {k: f"audio/{SUB}/{k}.mp3" for k in tips}
open("/tmp/zh_audio.json", "w").write(json.dumps(zh, ensure_ascii=False))
