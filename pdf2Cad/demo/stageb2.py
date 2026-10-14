# -*- coding: utf-8 -*-
"""Stage B step 2: plan-view axis clustering + callout OCR for one sheet.
Usage: python stageb2.py 007"""
import json, sys, math, re
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw

SHEET = sys.argv[1] if len(sys.argv) > 1 else '007'
d = json.load(open(f'demo/stageb_{SHEET}.json', encoding='utf-8'))
lines, circles = d['lines'], d['circles']

# plan view region (lower-left big view) — tune per sheet
REG = {'007': (60, 470, 1760, 1290), '004': (100, 400, 1420, 1070),
       '010': (120, 560, 2140, 1460), '008': (110, 540, 2250, 1460)}[SHEET]
RX0, RY0, RX1, RY1 = REG

segs = []
for ln in lines:
    (x0, y0), (x1, y1) = ln['a'], ln['b']
    mx, my = (x0+x1)/2, (y0+y1)/2
    if not (RX0 <= mx <= RX1 and RY0 <= my <= RY1):
        continue
    L = math.dist(ln['a'], ln['b'])
    if L < 3:
        continue
    ang = math.degrees(math.atan2(y1-y0, x1-x0)) % 180
    segs.append({'a': [x0,y0], 'b': [x1,y1], 'len': L, 'ang': ang})
print(f'plan segments: {len(segs)}')

# collinear clustering
parent = list(range(len(segs)))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i
def params(s):
    ax, ay = s['a']; bx, by = s['b']
    dx, dy = bx-ax, by-ay
    L = math.hypot(dx,dy) or 1
    return dx/L, dy/L, ax, ay, L
P = [params(s) for s in segs]
def colin(i, j):
    dxi,dyi,axi,ayi,Li = P[i]
    dxj,dyj,axj,ayj,Lj = P[j]
    if abs(dxi*dxj + dyi*dyj) < 0.999: return False
    perp = abs(dxj*(ayi-ayj) - dyj*(axi-axj))
    if perp > 3.0: return False
    t1 = (axj-axi)*dxi + (ayj-ayi)*dyi
    return (t1+Lj) > -5 and t1 < Li+5
buckets = {}
for i,s in enumerate(segs):
    buckets.setdefault(round(s['ang']/3), []).append(i)
for key, idxs in buckets.items():
    for bi in range(len(idxs)):
        for bj in range(bi+1, len(idxs)):
            i,j = idxs[bi], idxs[bj]
            ri,rj = find(i), find(j)
            if ri!=rj and colin(i,j): parent[rj]=ri
groups = {}
for i in range(len(segs)): groups.setdefault(find(i), []).append(i)

clusters = []
for idxs in groups.values():
    dxi,dyi,_,_,_ = P[idxs[0]]
    if dxi < 0: dxi,dyi = -dxi,-dyi
    ox,oy = segs[idxs[0]]['a']
    ts = []
    for i in idxs:
        for p in (segs[i]['a'], segs[i]['b']):
            ts.append((p[0]-ox)*dxi + (p[1]-oy)*dyi)
    t0,t1 = min(ts), max(ts)
    if t1-t0 < 60: continue
    a = [ox+dxi*t0, oy+dyi*t0]
    b = [ox+dxi*t1, oy+dyi*t1]
    ang = math.degrees(math.atan2(dyi,dxi)) % 180
    clusters.append({'a': a, 'b': b, 'ext': t1-t0, 'ang': round(ang,1),
                     'nseg': len(idxs), 'gap': round((t1-t0)/max(1,len(idxs)),1)})
clusters.sort(key=lambda c: -c['ext'])
print(f'axis clusters(>60pt): {len(clusters)}')

# callout circles in plan region
plan_circles = [c for c in circles if RX0 <= c['c'][0] <= RX1 and RY0 <= c['c'][1] <= RY1
                and 6 < c['r'] < 16]
print(f'callout circles in plan: {len(plan_circles)}')

json.dump({'clusters': clusters, 'plan_circles': plan_circles},
          open(f'demo/stageb2_{SHEET}.json','w',encoding='utf-8'), ensure_ascii=False)

# overlay viz
import fitz
doc = fitz.open(f'图纸/37-SA36901S-T0121-{SHEET}.pdf')
page = doc[0]
DPI = 110; Z = DPI/72.0
pix = page.get_pixmap(dpi=DPI, clip=fitz.Rect(RX0, RY0, RX1, RY1))
img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
dr = ImageDraw.Draw(img)
for i, c in enumerate(clusters):
    col = (255,60,60) if c['ext'] > 800 else ((0,150,60) if 200 < c['ext'] <= 800 else (60,60,255))
    dr.line([((c['a'][0]-RX0)*Z,(c['a'][1]-RY0)*Z), ((c['b'][0]-RX0)*Z,(c['b'][1]-RY0)*Z)],
            fill=col, width=2)
for c in plan_circles:
    x,y = (c['c'][0]-RX0)*Z, (c['c'][1]-RY0)*Z
    r = c['r']*Z
    dr.ellipse([x-r,y-r,x+r,y+r], outline=(255,140,0), width=2)
img.save(f'demo/stageb2_{SHEET}_overlay.png')
print('saved overlay', img.size)
