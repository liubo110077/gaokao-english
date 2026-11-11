import os

# Auto-load .env from project root (gitignored)
_env = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(_env):
    with open(_env) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip())

API_KEY     = os.environ.get("VOLC_API_KEY", "")
RESOURCE_ID = "seed-tts-2.0"
SPEAKER     = "zh_male_shaonianzixin_uranus_bigtts"   # 中文讲解用
EN_SPEAKER  = "zh_male_shaonianzixin_uranus_bigtts"   # 英文单词发音用（可换英文speaker）
