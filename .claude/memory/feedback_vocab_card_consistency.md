---
name: feedback_vocab_card_consistency
description: Vocab cards must show, define and pronounce the same word; clicking a card only plays audio, never jumps to the passage
metadata:
  type: feedback
---

On every vocab card the displayed word, its meaning (`vocab-meaning`) and the audio played by `vocabClick('…')` must all be about that same word.

**Why:** Cards were derived from tooltips. A tooltip phrase like `candle-lit dinner` produced a card "lit" whose meaning was still the whole phrase ("烛光晚餐"); `include` played the audio of `includes`; clicking a card also scrolled to the passage, so the learner could not review words. The user rejected all three.

**How to apply:**
- `vocabClick(word)` must call only `speakWord(word)` — no `highlightWord`, no scrolling.
- The argument of `vocabClick` = the text shown on the card (lemma / phrase as displayed), not the tooltip phrase. For "credit ... to ..." speak "credit to".
- If a card word is taken out of a longer phrase, give the meaning of the WORD and put the phrase in the example line.
- A sentence-jump link inside question analyses ("原文定位") is a different feature; the user only objected to the vocab-card jump.
- Every word read aloud needs `audio/<passage>/en-word-<slug>.mp3`; otherwise the page falls back to browser speech synthesis, which is often silent on iPad/Safari. Check coverage after adding cards.
