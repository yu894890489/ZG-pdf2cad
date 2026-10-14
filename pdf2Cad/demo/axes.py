# -*- coding: utf-8 -*-
"""Step 5: collinear clustering of all segments -> member axes in the detail view."""
import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('demo/data.json', encoding='utf-8'))

RX0, RY0, RX1, RY1 = 850, 500, 2100, 1330   # expanded detail region

segs = []
for ln in data['lines']:
    (x0, y0), (x1, y1) = ln['a'], ln['b']
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    if not (RX0 <= mx <= RX1 and RY0 <= my <= RY1):
        continue
    L = math.dist(ln['a'], ln['b'])
    if L < 3:
        continue
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180
    segs.append({'a': [x0, y0], 'b': [x1, y1], 'len': L, 'ang': ang,
                 'w': ln.get('w', 0)})
print(f'segments in region: {len(segs)}')

# ---- collinear clustering ----
n = len(segs)
parent = list(range(n))

def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i

def axis_params(s):
    ax, ay = s['a']; bx, by = s['b']
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy) or 1
    return dx / L, dy / L, ax, ay, L

params = [axis_params(s) for s in segs]

def colinear(i, j):
    dxi, dyi, axi, ayi, Li = params[i]
    dxj, dyj, axj, ayj, Lj = params[j]
    if abs(dxi * dxj + dyi * dyj) < 0.999:      # angle within ~2.5 deg
        return False
    # perpendicular distance of j start from i line
    perp = abs(dxj * (ayi - ayj) - dyj * (axi - axj))
    if perp > 3.0:
        return False
    # projection overlap
    t1 = (axj - axi) * dxi + (ayj - ayi) * dyi
    t2 = t1 + Lj
    return t2 > -5 and t1 < Li + 5

# bucket by rounded angle to reduce pairs
from collections import defaultdict
buckets = defaultdict(list)
for i, s in enumerate(segs):
    buckets[round(s['ang'] / 3)].append(i)

for key, idxs in buckets.items():
    for bi in range(len(idxs)):
        for bj in range(bi + 1, len(idxs)):
            i, j = idxs[bi], idxs[bj]
            ri, rj = find(i), find(j)
            if ri != rj and colinear(i, j):
                parent[rj] = ri

groups = {}
for i in range(n):
    groups.setdefault(find(i), []).append(i)

clusters = []
for idxs in groups.values():
    # axis extent via projections on dominant direction
    dxi, dyi, *_ = params[idxs[0]]
    if dxi < 0: dxi, dyi = -dxi, -dyi
    pts = []
    for i in idxs:
        s = segs[i]
        for p in (s['a'], s['b']):
            pts.append((p[0] - segs[idxs[0]]['a'][0]) * dxi + (p[1] - segs[idxs[0]]['a'][1]) * dyi)
    ext = max(pts) - min(pts)
    if ext < 80:
        continue
    # endpoints in world coords: project back
    ox, oy = segs[idxs[0]]['a']
    t0, t1 = min(pts), max(pts)
    a = [ox + dxi * t0, oy + dyi * t0]
    b = [ox + dxi * t1, oy + dyi * t1]
    ang = math.degrees(math.atan2(dyi, dxi)) % 180
    kind = 'V' if abs(abs(ang) - 90) < 3 else ('H' if abs(ang) < 3 or abs(ang - 180) < 3 else 'D')
    clusters.append({'a': a, 'b': b, 'ext': ext, 'ang': round(ang, 1),
                     'kind': kind, 'nseg': len(idxs),
                     'gap': ext / max(1, len(idxs))})

clusters.sort(key=lambda c: -c['ext'])
print(f'axis clusters (>80pt): {len(clusters)}')
for c in clusters:
    print(f" {c['kind']} ang={c['ang']:6.1f} ({c['a'][0]:7.1f},{c['a'][1]:7.1f})-({c['b'][0]:7.1f},{c['b'][1]:7.1f}) ext={c['ext']:6.1f} nseg={c['nseg']:3d} gap={c['gap']:5.1f}")

json.dump(clusters, open('demo/axes.json', 'w'), ensure_ascii=False)
