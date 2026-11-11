---
name: feedback_pronunciation_local_dictionary_first
description: If the local Longman British dictionary has the word's audio, use it and do NOT generate that word with Volcano at all; Volcano only for what the dictionary lacks
metadata:
  type: feedback
---

**Rule:** Pronunciation of an English word/phrase = the real-voice British clip from the local Longman LDOCE5++ dictionary. If the dictionary has it, use it and NEVER call Volcano for that word (don't synthesize-then-overwrite either). Volcano TTS is only for items the dictionary cannot provide (most multi-word phrases, derived forms without their own entry such as `dining`, `reawakened`).

**Why:** Volcano/豆包 TTS reads single words badly (too short, not standard, e.g. `dining`). The user pointed to the local EuDic dictionary folder (`/Users/liubo/Documents/software/欧路拓展词典【小蓝LoMoyi】`), chose British English, and accepted that the repo is public (self-study use).

**How to apply:**
- Order for any new word/card/tooltip: FIRST run `tools/extract_longman_bre.py` (copies the dictionary clip and writes `tools/longman_slugs.json`); THEN run `gen_audio.py` — it reads that file and automatically skips `en-word-*` items whose slug is covered, so those words never reach Volcano.
- If you add words and forget the extractor, `gen_audio.py` would synthesize them with Volcano; re-run the extractor afterwards to replace them with the dictionary clip.
- Do not use a redirect entry's audio (dining→dine would be wrong); inflected forms keep TTS unless the dictionary has that exact entry.
- Chinese explanations, long-sentence analyses and the English sentence read-aloud stay on Volcano (少年梓辛); B篇 sentences were ElevenLabs.
- See [[reference_audio_pipeline]] for the commands and [[feedback_tts_preference]].
