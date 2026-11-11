---
name: feedback_explanations_simple_words_only
description: Tooltip/vocab-card explanations may only bring in simple, already-known words; no hard or unrelated vocabulary
metadata:
  type: feedback
---

When writing explanations (tooltips `data-tip`, vocab cards, analyses), any extra English words brought in (collocations, analogies, derivatives, synonyms) must be simple words a middle-school learner already knows. Never add hard or unrelated words. Goal: zero extra cognitive load.

**Why:** `flagship` explained with "fleet", `set menu` with "à la carte / prix fixe", `make waves` with "sensation / splash" were all rejected. The user then clarified the rule is "extra words OK only if simple".

**How to apply:**
- Etymology: split only into real components (flag + ship).
- Phrases: just explain them directly (wave = 波浪, make waves = 掀起波浪 → 引起轰动). No "同义替换 / 近义 / 反义 / 类比" chains of harder words.
- Keep basic collocations (strict with sb, generation gap); drop ones with hard words (loyal, faithful, spiritual, negotiable, companion, rewarding, conservative...). Never invent a wrong collocation (e.g. "reach a negotiation").
- After editing a tooltip, regenerate only that audio (see [[reference_audio_pipeline]]).
