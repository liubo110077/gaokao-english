---
name: reference_deploy_and_git
description: Site URL, GitHub Pages, and the git/network quirks (Clash proxy, concurrent edits, iPad caching) for this repo
metadata:
  type: reference
---

- Repo: github.com/liubo110077/gaokao-english (public, free plan). GitHub Pages serves `main`/root: https://liubo110077.github.io/gaokao-english/ (page cache ≈10 min).
- **Network:** git/curl to GitHub hang without the local Clash proxy. Use `git -c http.proxy=http://127.0.0.1:7897 …` (git does not read the macOS system proxy). Never store a GitHub token in the remote URL, in config or in memory files; pass it for one command only, and ask the user for a new one when needed.
- **Fetch before editing/pushing:** another session edits the same pages and audio in parallel (twice a push was rejected or conflicted). After a conflict, take the remote version and re-apply only what is still missing.
- No git identity is configured on this Mac: commit with `-c user.name="Liu Bo" -c user.email=…` (copy from `git log`), do not change global config. Stage explicit paths when other work is uncommitted.
- Shell gotchas: zsh does not word-split `$VAR` (use explicit `-c …` args); `wc -l` output has leading spaces, so `[ "$N" = "0" ]` fails — strip it. Verify a push with `git ls-remote` instead of trusting output.
- iPad "添加到主屏幕" caches hard: after updates, delete the icon, reload in Safari, add again. (Icons/manifest/service worker are not set up yet.)
- 考纲内/外 labels: check against `syllabus_words.json` / `词表/高考词表_PDF原版.csv` (e.g. `twist` is NOT in the 3500 list → 超纲). Do not label from memory.
