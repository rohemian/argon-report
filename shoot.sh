#!/bin/bash
# 로컬 점검용: site/cardN.html → png/cardN.png (gsk 필요, GitHub에서는 사용 안 함)
mkdir -p png; cd site
for n in "$@"; do (gsk screenshot card$n.html --viewport '{"width":840,"height":900}' --scale 2 > ../png/shot$n.json 2>&1) & done; wait
cd ..; python3 - "$@" <<'PY'
import sys,re,subprocess
from PIL import Image
for n in sys.argv[1:]:
    s=open(f"png/shot{n}.json").read(); m=re.search(r'https://\S+?/api/files/s/\w+',s)
    if not m: print(n,"FAIL",s[:200]); continue
    u=m.group(0); subprocess.run(["gsk","download",u,"--save",f"png/card{n}.png"],capture_output=True)
    im=Image.open(f"png/card{n}.png"); w,h=im.size; print(n,u,w,h)
    for i,y in enumerate(range(0,h,1500)):
        im.crop((0,y,w,min(h,y+1500))).resize((w//2,(min(h,y+1500)-y)//2)).save(f"png/c{n}_{i}.png")
PY
