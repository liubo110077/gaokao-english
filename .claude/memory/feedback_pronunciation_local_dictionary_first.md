---
name: feedback_pronunciation_local_dictionary_first
description: For English word pronunciation, prefer the local Longman British dictionary audio; Volcano TTS is only the fallback
metadata:
  type: feedback
---

**Rule:** Pronunciation of an English word/phrase = the real-voice British clip from the local Longman LDOCE5++ dictionary FIRST. Use Volcano TTS only for items the dictionary cannot provide (most multi-word phrases, derived forms without their own entry such as `dining`, `reawakened`).

**Why:** Volcano/豆包 TTS reads single words badly (too short, not standard, e.g. `dining`). The user pointed to the local EuDic dictionary folder (`/Users/liubo/Documents/software/欧路拓展词典【小蓝LoMoyi】`), chose British English, and accepted that the repo is public (self-study use).

**How to apply:**
- Whenever a new word/card/tooltip is added, run `tools/extract_longman_bre.py` AFTER any Volcano generation, so dictionary clips overwrite TTS clips for words that have their own entry. Order matters: running Volcano generation later can overwrite the dictionary clip, so re-run the extractor.
- Do not use a redirect entry's audio (dining→dine would be wrong); inflected forms keep TTS unless the dictionary has that exact entry.
- Chinese explanations, long-sentence analyses and the English sentence read-aloud stay on Volcano (少年梓辛); B篇 sentences were ElevenLabs.
- See [[reference_audio_pipeline]] for the commands and [[feedback_tts_preference]].
