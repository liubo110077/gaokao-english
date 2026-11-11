"""Auto-tag tooltip spans with data-level based on syllabus_expanded.json.

Usage:
    python3 mark_levels.py              # all 4 passages
    python3 mark_levels.py --passage D  # one passage
    python3 mark_levels.py --dry-run    # print changes, don't save

Level values written to data-level="...":
    "超纲"  — word not in 高考课程标准 (or any derivation)
    "拓展"  — in standard, 拓展词汇 (**级别)
    "选必"  — in standard, 选择性必修 (*级别)
    ""      — 核心必修词, no badge needed (attribute not written)
"""
import csv, html as htmlmod, re, sys, os

_BASE = os.path.dirname(os.path.abspath(__file__))

CSV_PATH = os.path.join(_BASE, '词表', '高考词表_含变形.csv')
with open(CSV_PATH, encoding='utf-8') as f:
    EXPANDED = {row['word']: row['level'] for row in csv.DictReader(f)}

PASSAGE_MAP = {
    'A': '2023-甲卷-A-Bangkok.html',
    'B': '2023-甲卷-B-DIY.html',
    'C': '2023-甲卷-C-Socrates.html',
    'D': '北京卷-D-Friends.html',
}

# Words too short or too common to determine phrase level
STOP = {
    'a','an','the','of','in','on','at','to','for','by','as','it','is','be',
    'or','and','with','out','up','into','from','its','this','that','not','no',
    'i','my','his','her','their','your','our','you','we','they','he','she',
    's','d','ll','t','re','m','ve','n','more','most','very','than','so',
    'just','even','only','also','much','many','some','any','all','each',
    'both','few','how','what','when','where','who','which','do','did',
    'has','have','had','was','were','am','are','been','being','get','got',
}

def phrase_level(phrase):
    """Return raw level code: '', '*', '**', or None (超纲)."""
    p = phrase.lower().strip()

    # 1. Exact phrase match (handles multi-word phrases like "according to")
    if p in EXPANDED:
        return EXPANDED[p]

    # 2. Word-by-word: level = worst level among content words
    words = re.findall(r"[a-zA-Z']+", phrase)
    content_levels = []
    for w in words:
        w = w.strip("'").lower()
        if len(w) < 3 or w in STOP or "'" in w:  # skip contractions (I'd, don't)
            continue
        if w in EXPANDED:
            content_levels.append(EXPANDED[w])
        else:
            return None   # 超纲: at least one content word not in standard

    if not content_levels:
        return ''   # only stop words → treat as 核心

    # Return the worst level (拓展 > 选必 > 核心)
    if '**' in content_levels: return '**'
    if '*'  in content_levels: return '*'
    return ''


def level_display(code):
    """Convert raw level code to display string for data-level attribute."""
    if code is None: return '超纲'
    if code == '**': return '拓展'
    if code == '*':  return '选必'
    return ''   # 核心 → no badge, don't write attribute


def process_file(path, dry_run=False):
    with open(path, encoding='utf-8') as f:
        original = f.read()

    # Step 1: strip any existing data-level attributes
    content = re.sub(r'\s+data-level="[^"]*"', '', original)

    # Step 2: for each <span class="tip" data-tip="..."> add data-level
    changes = 0

    def insert_level(m):
        nonlocal changes
        full_tag = m.group(0)                    # the entire opening <span ...>
        tip_raw  = htmlmod.unescape(m.group(1))  # unescaped data-tip value
        phrase   = tip_raw.split('|')[0].strip()

        code    = phrase_level(phrase)
        display = level_display(code)

        if not display:          # 核心 → nothing to add
            return full_tag

        changes += 1
        # Insert data-level="..." right after data-tip="..."
        return full_tag + f' data-level="{display}"'

    # Match the whole opening tag and capture data-tip value
    # Pattern: <span ...class="tip"... data-tip="VALUE"...>
    # We match the closing > of the opening tag and insert before it.
    def replacer(m):
        nonlocal changes
        before_tip = m.group(1)
        tip_val    = m.group(2)
        after      = m.group(3)
        tip_raw    = htmlmod.unescape(tip_val)
        phrase     = tip_raw.split('|')[0].strip()
        code       = phrase_level(phrase)
        display    = level_display(code)
        if display:
            changes += 1
            # Insert data-level as attribute BEFORE the closing '>' of the opening tag
            return f'{before_tip}data-tip="{tip_val}"{after[:-1]} data-level="{display}">'
        return f'{before_tip}data-tip="{tip_val}"{after}'

    # Capture: everything before data-tip, the tip value, everything after in same tag up to >
    pattern = r'(<span\b[^>]*?)data-tip="([^"]*)"([^>]*?>)'
    content = re.sub(pattern, replacer, content)

    fname = os.path.basename(path)
    if dry_run:
        print(f'[dry-run] {fname}: would add data-level to {changes} spans')
        return

    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'{fname}: tagged {changes} spans')
    else:
        print(f'{fname}: no changes')


def main():
    dry_run  = '--dry-run' in sys.argv
    passages = []
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--passage' and i < len(sys.argv):
            passages.append(sys.argv[i + 1].upper())

    if not passages:
        passages = list(PASSAGE_MAP.keys())

    for key in passages:
        path = os.path.join(_BASE, PASSAGE_MAP[key])
        process_file(path, dry_run=dry_run)


if __name__ == '__main__':
    main()
