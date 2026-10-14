# -*- coding: utf-8 -*-
"""001 全塔正视图轴线提取：silhouette + 水平横材 + 斜材 → axes001_full.json"""
import sys, os, json, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

d1 = json.load(open('demo/data001.json', encoding='utf-8'))
CX, Y_BOT, SC = 624.0, 3749.0, 135000.0/3632.0

def to_mm(x, y):
    return (x-CX)*SC, (Y_BOT-y)*SC

# 全塔: x_pt 100~1150, y_pt 90~3750
segs = []
for ln in d1['lines']:
    (xa, ya), (xb, yb) = ln['a'], ln['b']
    mx = (xa+xb)/2; my = (ya+yb)/2
    if 100 <= mx <= 1150 and 90 <= my <= 3740:
        X1, Z1 = to_mm(xa, ya); X2, Z2 = to_mm(xb, yb)
        if math.dist([X1,Z1],[X2,Z2]) > 80:
            segs.append(([X1,Z1],[X2,Z2]))
print(f'segs: {len(segs)}', flush=True)

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
    if ext < 500: continue
    axes.append({'a': [round(ox+uxi*t0), round(oy+uyi*t0)],
                 'b': [round(ox+uxi*t1), round(oy+uyi*t1)],
                 'ext': round(ext), 'nseg': len(idxs),
                 'ang': round(math.degrees(math.atan2(uyi, uxi)) % 180, 1)})

print(f'axes: {len(axes)}')
json.dump(axes, open('demo/axes001_full.json', 'w'), indent=1)

# 渲染提取结果
fig, ax = plt.subplots(figsize=(14, 20))
for a in axes:
    if a['ang'] < 2 or a['ang'] > 178:
        c = 'tab:blue'      # 水平
    elif 85 < a['ang'] < 95:
        c = 'tab:red'       # 竖直
    else:
        c = 'tab:green'     # 斜材
    ax.plot([a['a'][0], a['b'][0]], [a['a'][1], a['b'][1]], color=c, lw=0.8)
ax.set_aspect('equal'); ax.grid(True, alpha=0.2)
ax.set_title('001 extracted axes: blue=H red=V green=diag')
plt.tight_layout(); plt.savefig('demo/axes001_full.png', dpi=90)
print('saved demo/axes001_full.png')
