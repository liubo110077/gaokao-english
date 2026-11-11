import os

# Set env var: export VOLC_API_KEY=your_key
API_KEY     = os.environ.get("VOLC_API_KEY", "")
RESOURCE_ID = "seed-tts-2.0"
SPEAKER     = "zh_male_shaonianzixin_uranus_bigtts"   # 中文讲解用
EN_SPEAKER  = "zh_male_shaonianzixin_uranus_bigtts"   # 英文单词发音用（可换英文speaker）
