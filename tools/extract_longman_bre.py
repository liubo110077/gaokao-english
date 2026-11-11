"""Replace en-word-*.mp3 with Longman LDOCE5 British clips when the word has its OWN dictionary entry
(redirect entries such as dining->dine are skipped on purpose). Usage:
  python3 -m venv /tmp/mdv/env && /tmp/mdv/env/bin/pip install mdict-utils
  /tmp/mdv/env/bin/python tools/extract_longman_bre.py
Writes tools/longman_replaced.json (words replaced per passage)."""
import sys,re,html,os,json,shutil
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from mdict_utils.reader import MDD
from longman_lookup import L
D=os.environ.get("EUDIC_DICT_DIR","/Users/liubo/Documents/software/欧路拓展词典【小蓝LoMoyi】")
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+"/"
PAGES=[("2023-甲卷-A-Bangkok.html","2023-甲卷-A"),("2023-甲卷-B-DIY.html","2023-甲卷-B"),("2023-甲卷-C-Socrates.html","2023-甲卷-C"),("北京卷-D-Friends.html","北京卷-D")]
slug=lambda x:re.sub(r"[^a-z0-9]+","-",x.lower()).strip("-")
l=L()
def direct_bre(w):
    t=l.d.get(w.lower().strip())
    if not t or t.strip().startswith("@@@LINK"): return None
    m=re.search(r"sound://(media/english/breProns/[^\"'<> ]+\.mp3)",t)
    return m.group(1) if m else None
plan={}   # (dir, slug) -> (word, mddkey)
for f,d in PAGES:
    s=open(R+f,encoding="utf-8").read()
    ws=set(re.findall(r"(?:speakWord|vocabClick)\('([^'$]+)'\)",s))
    ws|={html.unescape(x).split("|")[0].strip() for x in re.findall(r'data-tip="([^"]*)"',s)}
    for w in ws:
        k=direct_bre(w)
        if k: plan[(d,slug(w))]=(w,"\\"+k.replace("/","\\"))
need={v[1] for v in plan.values()}
print("将使用词典英音的条目:",len(plan),"| 需提取文件:",len(need))
got={}
m=MDD(D+"/Longman/LDOCE5++ V 1-35.mdd")
for k,v in m.items():
    kk=k.decode() if isinstance(k,bytes) else k
    if kk in need:
        got[kk]=v
        if len(got)==len(need): break
print("实际取到:",len(got))
log={}
for (d,sl),(w,k) in sorted(plan.items()):
    if k not in got: continue
    open(f"{R}audio/{d}/en-word-{sl}.mp3","wb").write(got[k]); log.setdefault(d,[]).append(w)
json.dump(log,open(R+"tools/longman_replaced.json","w"),ensure_ascii=False,indent=1)
json.dump({d:sorted({slug(w) for w in ws}) for d,ws in log.items()},open(R+"tools/longman_slugs.json","w"),ensure_ascii=False,indent=1)  # gen_audio.py skips these slugs
for d,ws in log.items(): print(d,len(ws),"个")
miss=[(w,k) for (d,sl),(w,k) in plan.items() if k not in got]
print("没取到:",miss[:10])
