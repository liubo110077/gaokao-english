"""Look up Longman LDOCE5++ (.mdx) entries and their sound:// links.
Needs: pip install mdict-utils (python-lzo NOT required). Dictionary dir via env EUDIC_DICT_DIR."""
import sys,re,html as H
from mdict_utils.reader import MDX
import os
D=os.environ.get("EUDIC_DICT_DIR","/Users/liubo/Documents/software/欧路拓展词典【小蓝LoMoyi】")
class L:
    def __init__(s):
        s.d={}
        for k,v in MDX(D+"/Longman/LDOCE5++ V 1-35.mdx").items():
            key=(k.decode() if isinstance(k,bytes) else k).lower(); val=(v.decode("utf-8","ignore") if isinstance(v,bytes) else v)
            if key not in s.d or (len(val)>len(s.d[key]) and not val.strip().startswith("@@@LINK")): s.d[key]=val
    def get(s,w,depth=0):
        t=s.d.get(w.lower().strip())
        if t is None: return None
        m=re.match(r"@@@LINK=(.+)",t.strip())
        if m and depth<4: return s.get(m.group(1).strip(),depth+1)
        return t
    def sounds(s,w):
        t=s.get(w)
        if not t: return None
        am=re.findall(r"sound://(media/english/ameProns/[^\"'<> ]+\.mp3)",t)
        br=re.findall(r"sound://(media/english/breProns/[^\"'<> ]+\.mp3)",t)
        return (am[0] if am else None, br[0] if br else None)
