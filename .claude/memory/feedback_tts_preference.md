---
name: feedback_tts_preference
description: TTS tool preference for English learning app audio generation
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3ccc967e-34e7-495b-8016-b919cafa9a7d
  modified: 2026-11-05T07:29:49.281Z
---

Always use Volcano Engine TTS (`volc_tts_gen.py`) for all audio generation in this project. Never use Alibaba CosyVoice (`gen_tts.py`).

**Why:** CosyVoice sounded bad. The default `zh_female_vv_uranus_bigtts` (Vivi) also sounded too AI/anxious. The user chose **少年梓辛** (`zh_male_shaonianzixin_uranus_bigtts`) as the preferred voice — more natural and calm.

**How to apply:** When generating any TTS — tooltip phrases, sentence analyses, or new content — always run `volc_tts_gen.py`, never `gen_tts.py`.
