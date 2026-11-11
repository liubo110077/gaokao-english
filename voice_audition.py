"""Audition 少年梓辛 and related Volcano seed-tts-2.0 voices."""
import asyncio, json, os, struct, subprocess, uuid

from volc_config import API_KEY  # read from env VOLC_API_KEY or .env (not committed)
RESOURCE_ID = "seed-tts-2.0"
SAMPLE_RATE = 24000
URL         = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"

SAMPLE_TEXT = "第一句就出现了 a dab hand——不用认识这个词。后面紧跟 when it comes to DIY，下一句 Skilled at putting up shelves，三句一串，你就知道 a dab hand 是某方面特别拿手的人。"

SPEAKERS = [
    ("A-当前Vivi",   "zh_female_vv_uranus_bigtts"),
    ("B-少年梓辛",   "zh_male_shaonianzixin_uranus_bigtts"),
    ("C-深夜播客",   "zh_male_shenyeboke_uranus_bigtts"),
    ("D-渊博小叔",   "zh_male_yuanboxiaoshu_uranus_bigtts"),
    ("E-温柔小哥",   "zh_male_wenrouxiaoge_uranus_bigtts"),
]

E_START_CONN=1; E_FINISH_CONN=2; E_START_SESSION=100
E_FINISH_SESSION=102; E_SESSION_FINISHED=152
E_TASK_REQUEST=200; E_TTS_RESPONSE=352

def frame(event, payload=b"{}", session_id=""):
    data = b"\x11\x14\x10\x00" + struct.pack(">i", event)
    if session_id:
        sid = session_id.encode()
        data += struct.pack(">I", len(sid)) + sid
    return data + struct.pack(">I", len(payload)) + payload

def parse_frame(data):
    if not isinstance(data, bytes) or len(data) < 4 or data[0] != 0x11:
        raise RuntimeError("Invalid frame")
    msg_type = data[1] >> 4; pos = 4
    def ri():
        nonlocal pos; v = struct.unpack_from(">I", data, pos)[0]; pos += 4; return v
    def rf():
        nonlocal pos; s = ri(); v = data[pos:pos+s]; pos += s; return v
    if msg_type == 0xF: code = ri(); rf(); raise RuntimeError(f"TTS error={code}")
    event = ri(); fields = []
    while pos < len(data): fields.append(rf())
    return msg_type, event, fields[-1] if fields else b""

def pcm_to_mp3(pcm, out):
    subprocess.run(["ffmpeg","-y","-f","s16le","-ar",str(SAMPLE_RATE),"-ac","1",
                    "-i","pipe:0","-codec:a","libmp3lame","-q:a","2",out],
                   input=pcm, capture_output=True, check=True)

async def synthesize(text, speaker):
    from websockets.legacy.client import connect
    sid = str(uuid.uuid4())
    hdrs = {"X-Api-Key": API_KEY, "X-Api-Resource-Id": RESOURCE_ID,
            "X-Api-Connect-Id": str(uuid.uuid4())}
    ws = await connect(URL, extra_headers=hdrs, max_size=10*1024*1024,
                       max_queue=16, open_timeout=10, close_timeout=5)
    try:
        await ws.send(frame(E_START_CONN)); parse_frame(await ws.recv())
        p = json.dumps({"req_params":{"speaker":speaker,"audio_params":{"format":"pcm","sample_rate":SAMPLE_RATE}}}).encode()
        await ws.send(frame(E_START_SESSION, p, sid)); parse_frame(await ws.recv())
        await ws.send(frame(E_TASK_REQUEST, json.dumps({"req_params":{"text":text}}).encode(), sid))
        await ws.send(frame(E_FINISH_SESSION, session_id=sid))
        chunks = []
        while True:
            mt, ev, payload = parse_frame(await ws.recv())
            if mt == 0xB and ev == E_TTS_RESPONSE: chunks.append(payload)
            elif ev == E_SESSION_FINISHED: break
        await ws.send(frame(E_FINISH_CONN)); parse_frame(await ws.recv())
    finally:
        await ws.close()
    return b"".join(chunks)

async def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    for label, speaker in SPEAKERS:
        out = os.path.join(out_dir, f"voice-test-{label}.mp3")
        try:
            pcm = await synthesize(SAMPLE_TEXT, speaker)
            pcm_to_mp3(pcm, out)
            print(f"  ✓ {label} [{speaker}]")
        except Exception as e:
            print(f"  ✗ {label} [{speaker}]: {e}")

asyncio.run(main())
