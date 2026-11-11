"""Build syllabus_expanded.json from all dictionary sources.

Sources (in order):
  A. syllabus_words.json  — 3,078 official base words
  B. ldoce_family.json    — LDOCE Word family derivations
  C. ldoce_inflections.json — LDOCE irregular inflections
  D. @@@LINK multi-pass convergence (LDOCE5++ / Collins / OELD)
  E. MW dot-notation morphological derivations
  F. PDF bracket-variants (manual additions)

Level rule: "lowest level wins" — if a word appears in multiple
  word families, it inherits the most common (核心 > 选必 > 拓展) level.
  BASE words always keep their syllabus level (forced at end).

Filters applied to @@@LINK entries:
  1. form must match ^[a-z]+$ (no hyphens/spaces)
  2. Length: len(form) - len(inter) <= MAX_LEN_DIFF per hop (default 8)
  3. PP+s: reject form = pure_past_participle + s/es
  4. Double-s guard: reject form = inter + s when inter ends in s

Run:
    python3 build_expanded.py
    python3 build_expanded.py --dry-run
"""
import json, re, sys, os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    from mdict_utils.reader import MDX
except ImportError:
    MDX = None

VALID        = re.compile(r'^[a-z]+$')
MAX_LEN_DIFF = 8  # max chars added per hop

LEVEL_ORDER = {'': 0, '*': 1, '**': 2}

# Abbreviations / noise that slip in via @@@LINK (e.g. mm→millimetre)
BLOCKLIST = {
    # abbreviations that slip in via @@@LINK
    'bc','cm','cw','gw','gy','ii','iw','km','mi','mm','mr','ms','pe','tn','uk',
    'mmm',
    # MW compound-word false positives (back·break·ing → back, etc.)
    'backbreaking',
}

# ── Paths ────────────────────────────────────────────────────────────────
DICT_PATHS = [
    '/Volumes/新加卷/欧路拓展词典【小蓝LoMoyi】/Longman/LDOCE5++ V 1-35.mdx',
    '/Volumes/新加卷/欧路拓展词典【小蓝LoMoyi】/Collins/CollinsCOBUILDOverhaul V 2-30.mdx',
    '/Volumes/新加卷/欧路拓展词典【小蓝LoMoyi】/Oxford/OELDOnlineV1-51.mdx',
]
MW_PATH = '/Volumes/新加卷/欧路拓展词典【小蓝LoMoyi】/韦氏高阶学习词典.mdx'

# MW derivational suffixes
MW_DERIV_SFXS = {
    'al','ial','ual','ful','less','ous','ious','eous',
    'ive','ative','itive','ment','ness',
    'tion','sion','ation','ition',
    'er','or','ist','ism','ize','ise','ized','ised',
    'ly','ily','ingly','ally','ually',
    'able','ible','ary','ery','ory','ent','ant','ic','ical',
    'ing','ed','s','es','ies',
}

# Manual PDF bracket-variants: (variant, main_word_in_BASE)
PDF_VARIANTS = [
    ('analyze','analyse'), ('apologize','apologise'), ('behavior','behaviour'),
    ('centimeter','centimetre'), ('center','centre'), ('civilization','civilisation'),
    ('color','colour'), ('criticize','criticise'), ('defense','defence'),
    ('dialog','dialogue'), ('disk','disc'), ('favorite','favourite'),
    ('fiber','fibre'), ('flavor','flavour'), ('honor','honour'),
    ('kilometer','kilometre'), ('labor','labour'), ('meter','metre'),
    ('millimeter','millimetre'), ('neighbor','neighbour'), ('neighborhood','neighbourhood'),
    ('organization','organisation'), ('program','programme'), ('realize','realise'),
    ('recognize','recognise'),
    ('ad','advertisement'), ('bicycle','bike'), ('bye','goodbye'),
    ('criteria','criterion'), ('dad','father'), ('exam','examination'),
    ('fridge','refrigerator'), ('grandma','grandmother'), ('grandpa','grandfather'),
    ('gram','gramme'), ('kilo','kilogramme'), ('kilogram','kilogramme'),
    ('kilogramme','gramme'),
    ('lab','laboratory'), ('lab','lab'),
    ('mathematics','maths'), ('laboratory','lab'), ('examination','exam'),
    ('media','medium'), ('mum','mother'), ('photo','photograph'),
    ('pop','popular'), ('till','until'), ('tv','television'),
    ('towards','toward'), ('teeth','tooth'),
    # adjective forms not captured by @@@LINK
    ('teenage','teenager'),
    # humorous is in syllabus but humour/humor (the noun) is not — add both spellings
    ('humour','humorous'), ('humor','humorous'),
    # slash pairs from PDF
    ('bride','bridegroom'), ('bridegroom','bride'),
    ('chairman','chairwoman'), ('chairwoman','chairman'),
    ('policeman','policewoman'), ('policewoman','policeman'),
    ('salesman','saleswoman'), ('saleswoman','salesman'),
    # full forms
    ('kilogram','kilogramme'),
]

# ── Helpers ──────────────────────────────────────────────────────────────

def load_json(path):
    with open(os.path.join(_BASE_DIR, path), encoding='utf-8') as f:
        return json.load(f)


def add(expanded, word, level):
    """Add word at level; lowest level wins ('' < '*' < '**')."""
    w = word.lower().strip()
    if not (VALID.match(w) and len(w) >= 2 and level in ('', '*', '**')):
        return False
    if w in BLOCKLIST:
        return False
    current = expanded.get(w)
    if current is None or LEVEL_ORDER[level] < LEVEL_ORDER[current]:
        expanded[w] = level
        return True
    return False


def build_pure_pp_set(inflections, pos_map, base):
    """Words that are pure past participles — cannot take noun plural -s."""
    pp = set()
    for b, forms in inflections.items():
        for f in forms:
            f = f.lower()
            if f == b or f.endswith('s') or f.endswith('ing'):
                continue
            if f == b + 'ed':
                continue
            if re.search(r'(en|wn)$', f):
                if 'noun' not in pos_map.get(f, []) and f not in base:
                    pp.add(f)
    return pp


def should_accept(form, inter, pure_pp):
    """Return (accept, reason). inter is the immediate target of @@@LINK."""
    # Length filter per hop
    if len(form) - len(inter) > MAX_LEN_DIFF:
        return False, 'too_long'
    # Double-s guard: form = inter + s, but inter already ends in s
    if form.endswith('s') and form[:-1] == inter and inter.endswith('s'):
        return False, 'double_s'
    # PP+s filter: form is a pure past participle + s/es
    if form.endswith('s') and form[:-1] in pure_pp:
        return False, 'pp_plus_s'
    if form.endswith('es') and form[:-2] in pure_pp:
        return False, 'pp_plus_es'
    return True, 'ok'


def build_link_map(dict_paths):
    """Scan all MDX files once; return {form: inter} with first-dict priority."""
    link_map = {}
    for path in dict_paths:
        mdx = MDX(path)
        for key, val in mdx.items():
            k = (key.decode() if isinstance(key, bytes) else key).lower().strip()
            v = (val.decode() if isinstance(val, bytes) else val).strip()
            if not v.startswith('@@@LINK'):
                continue
            if not VALID.match(k):
                continue
            inter = v.replace('@@@LINK=', '').strip().lower()
            if not VALID.match(inter) or ' ' in inter:
                continue
            if k != inter and k not in link_map:
                link_map[k] = inter
    return link_map


# ── Main build ───────────────────────────────────────────────────────────

def build():
    base_raw = load_json('syllabus_words.json')
    BASE = {w.lower(): v for w, v in base_raw.items()
            if re.match(r'^[a-z]{2,}$', w.lower())}
    FAMILY  = load_json('ldoce_family.json')
    INFLECT = load_json('ldoce_inflections.json')
    POS_MAP = load_json('ldoce_pos.json')

    PURE_PP = build_pure_pp_set(INFLECT, POS_MAP, BASE)
    print(f"Pure PP set: {len(PURE_PP)} words  (shown: {'shown' in PURE_PP})")

    expanded = {}

    # A. BASE words (forced)
    for bw, lv in BASE.items():
        expanded[bw] = lv

    # B. LDOCE Word family — lowest level wins across all families
    for bw, lv in BASE.items():
        for fw in FAMILY.get(bw, []):
            add(expanded, fw, lv)

    # C. LDOCE irregular inflections
    for bw, lv in BASE.items():
        for iw in INFLECT.get(bw, []):
            add(expanded, iw, lv)

    # D. @@@LINK multi-pass convergence
    if MDX:
        link_map = build_link_map(DICT_PATHS)
        print(f"@@@LINK map size: {len(link_map):,}")

        rejected = {'too_long': 0, 'double_s': 0, 'pp_plus_s': 0, 'pp_plus_es': 0}
        for pass_num in range(6):
            added = 0
            for form, inter in link_map.items():
                if form in expanded:
                    continue
                if inter not in expanded:
                    continue
                ok, reason = should_accept(form, inter, PURE_PP)
                if not ok:
                    rejected[reason] += 1
                    continue
                if add(expanded, form, expanded[inter]):
                    added += 1
            print(f"  @@@LINK pass {pass_num+1}: +{added} entries")
            if added == 0:
                break

        print(f"  @@@LINK rejected: {rejected}")

    # E. MW dot-notation morphological derivations
    if MDX and os.path.exists(MW_PATH):
        mw_added = 0
        mdx_mw = MDX(MW_PATH)
        for key, val in mdx_mw.items():
            k = (key.decode() if isinstance(key, bytes) else key).lower().strip()
            v = (val.decode() if isinstance(val, bytes) else val).strip()
            if v.startswith('@@@LINK'):
                continue
            plain = re.sub(r'<[^>]+>', ' ', v)
            dot_m = re.search(r'[a-z][a-z]*(?:·[a-z]+)+', plain[:300])
            if not dot_m:
                continue
            dot_word = dot_m.group()
            if dot_word.replace('·', '') != k:
                continue
            parts = dot_word.split('·')
            if parts[-1] not in MW_DERIV_SFXS:
                continue
            for end in range(len(parts) - 1, 0, -1):
                prefix = ''.join(parts[:end])
                if len(prefix) >= 4 and prefix in expanded:
                    ok, _ = should_accept(k, prefix, PURE_PP)
                    if ok and add(expanded, k, expanded[prefix]):
                        mw_added += 1
                    break
        print(f"MW derivations added: {mw_added}")

    # F. PDF bracket-variants & slash-pairs
    for variant, main in PDF_VARIANTS:
        lv = BASE.get(main) or expanded.get(main)
        if lv is not None:
            add(expanded, variant, lv)

    # G. BASE re-override (force correct levels for syllabus words)
    for bw, lv in BASE.items():
        expanded[bw] = lv

    # H. Final cleanup
    cleaned = {w: lv for w, lv in expanded.items()
               if len(w) >= 2 and lv in ('', '*', '**') and w not in BLOCKLIST}

    print(f"\nFinal: {len(cleaned):,} entries")
    print(f"  核心={sum(1 for v in cleaned.values() if v==''):,}")
    print(f"  选必={sum(1 for v in cleaned.values() if v=='*'):,}")
    print(f"  拓展={sum(1 for v in cleaned.values() if v=='**'):,}")
    return cleaned


CSV_PATH = os.path.join(_BASE_DIR, '词表', '高考词表_含变形.csv')


def save_csv(result):
    with open(CSV_PATH, 'w', encoding='utf-8') as f:
        f.write('word,level\n')
        for w in sorted(result):
            f.write(f'{w},{result[w]}\n')
    print(f"Saved → {CSV_PATH}")


if __name__ == '__main__':
    dry = '--dry-run' in sys.argv
    result = build()
    if dry:
        print("(dry-run, not saved)")
    else:
        save_csv(result)
