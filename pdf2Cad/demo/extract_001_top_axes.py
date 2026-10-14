# -*- coding: utf-8 -*-
"""001 顶部轴线聚类：提取地线支架(W形)与横担(芬克式)的精确轮廓坐标"""
import sys, os, json, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

d1 = json.load(open('demo/data001.json', encoding='utf-8'))
CX, Y_BOT, SC = 624.0, 3749.0, 135000.0/3632.0

def to_mm(x, y):
    return (x-CX)*SC, (Y_BOT-y)*SC

# 收集顶部区域线段 → mm
segs = []
for ln in d1['lines']:
    (xa, ya), (xb, yb) = ln['a'], ln['b']
    mx = (xa+xb)/2; my = (ya+yb)/2
    if 350 <= mx <= 900 and 90 <= my <= 300:
        X1, Z1 = to_mm(xa, ya); X2, Z2 = to_mm(xb, yb)
        if math.dist([X1,Z1],[X2,Z2]) > 100:
            segs.append(([X1,Z1],[X2,Z2]))
print(f'segs in top region: {len(segs)}')

# 共线聚类
n = len(segs)
parent = list(range(n))
def find(i):
    while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
    return i
P = []
for a, b in segs:
    dx, dy = b[0]-a[0], b[1]-a[1]
    L = math.hypot(dx, dy) or 1
    P.append((dx/L, dy/L, a[0], a[1], L))
def colinear(i, j):
    uxi,uyi,axi,ayi,Li = P[i]
    uxj,uyj,axj,ayj,Lj = P[j]
    dot = uxi*uxj + uyi*uyj
    if abs(dot) < 0.999: return False
    if dot < 0: uxj,uyj = -uxj,-uyj
    perp = abs(uxj*(ayi-ayj) - uyj*(axi-axj))
    if perp > 60: return False
    t1 = (axj-axi)*uxi + (ayj-ayi)*uyi
    return (t1+Lj) > -100 and t1 < Li+100
buckets = {}
for i in range(n):
    ang = round(math.degrees(math.atan2(P[i][1], P[i][0])) % 180 / 1.5)
    buckets.setdefault(ang, []).append(i)
for key, idxs in buckets.items():
    for bi in range(len(idxs)):
        for bj in range(bi+1, len(idxs)):
            i, j = idxs[bi], idxs[bj]
            ri, rj = find(i), find(j)
            if ri != rj and colinear(i, j): parent[rj] = ri
groups = {}
for i in range(n): groups.setdefault(find(i), []).append(i)

axes = []
for idxs in groups.values():
    uxi, uyi, ox, oy, _ = P[idxs[0]]
    if uxi < 0: uxi, uyi = -uxi, -uyi
    ts = []
    for i in idxs:
        for p in (segs[i][0], segs[i][1]):
            ts.append((p[0]-ox)*uxi + (p[1]-oy)*uyi)
    t0, t1 = min(ts), max(ts)
    ext = t1 - t0
    if ext < 800: continue
    axes.append({'a': [round(ox+uxi*t0), round(oy+uyi*t0)],
                 'b': [round(ox+uxi*t1), round(oy+uyi*t1)],
                 'ext': round(ext), 'nseg': len(idxs),
                 'ang': round(math.degrees(math.atan2(uyi, uxi)) % 180, 1)})

axes.sort(key=lambda a: -a['ext'])
print(f'\naxes (ext>800mm): {len(axes)}')
for a in axes:
    print(f"  ({a['a'][0]:>7},{a['a'][1]:>7}) -> ({a['b'][0]:>7},{a['b'][1]:>7})  ext={a['ext']:>6} ang={a['ang']:>5} n={a['nseg']}")
json.dump(axes, open('demo/axes001_top.json', 'w'), indent=1)
