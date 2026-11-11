---
name: reference_audio_pipeline
description: How audio is produced for the four passages (Volcano TTS + Longman British clips), file naming, scripts and the --only rule
metadata:
  type: reference
---

**File naming** (`audio/<passage>/`, passages: 2023-甲卷-A/B/C, 北京卷-D): `en-sNN.mp3` sentence read-aloud; `en-word-<slug>.mp3` English word/phrase pronunciation; `<slug>.mp3` Chinese tooltip explanation; `analysis-N.mp3` long-sentence analysis. slug = lowercase, non-alphanumerics → "-".

**Generating (Volcano seed-tts-2.0, voice 少年梓辛 `zh_male_shaonianzixin_uranus_bigtts`)**
- `python3 gen_audio.py <repo> <page.html> <audio-subdir> [--en-only] [--only=slug,slug]` — HTTP API, no ffmpeg/websockets needed; skips items whose text hash is unchanged (`.tts_cache.json`).
- ALWAYS pass `--only=` (or edit-then-run on one passage) when only a few texts changed. Running without it can regenerate and overwrite many existing clips (it did once on B and once on A/C/D).
- It scans `data-tip`, `speakWord('…')`, `vocabClick('…')`, `sentences = [...]`, and `<div class="analysis" id="analysis-N">`.
- Never hardcode the API key. Scripts read `VOLC_API_KEY` via `volc_config.py` (env or a gitignored `.env`); the local helper reads `~/.volc_tts.env`. The repo is PUBLIC; a key was leaked once in old commits and must be rotated, not just deleted.

**Real-voice British clips for single words (decision: user chose British, accepted that the repo is public)**
- Priority rule: dictionary clip first, covered words are never synthesized (`gen_audio.py` skips slugs in `tools/longman_slugs.json`; see [[feedback_pronunciation_local_dictionary_first]]).
- Source: local Longman LDOCE5++ MDict in the user's EuDic folder. `tools/extract_longman_bre.py` copies the British clip into `en-word-<slug>.mp3` only when the word has its OWN dictionary entry (redirects like dining→dine are skipped). `tools/longman_replaced.json` lists what was replaced (≈75 words).
- Needs a venv with `pip install mdict-utils` (python-lzo is not needed/does not build). MDD has no `get()`; iterate `items()`.
- Phrases (≈100 items such as manage to, put up) are not in the dictionary → they stay Volcano TTS.
- Very short single words sounded too short with Volcano; for words with no dictionary entry (`dining`, `personalise`) use speech_rate -15 and `additions={"silence_duration":300}`.
- B篇 sentence audio `en-s00..14` came from ElevenLabs (`gen_en_tts.py`, Daniel); all other passages use Volcano for sentences.
