# -*- coding: utf-8 -*-
"""Extract crossarm trusses DIRECTLY from 001's front view (the authoritative orthographic).
Bands: 第一层(地线支架) y 100-290, 第二层(中导线) y 590-750, 第三层(下导线) y 925-1150.
Scale 37.17mm/pt, centerline x=624. Place in y=0 plane (depth handled later)."""
import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')

d1 = json.load(open('demo/data001.json', encoding='utf-8'))
CX, Y_BOT = 624.0, 3749.0
SC = 135000.0 / 3632.0

BANDS = [
    ('L1', 129571.0, 100, 290),   # 第一层 地线支架 (构件1,2)
    ('L2', 114297.0, 590, 750),   # 第二层 中导线 (构件3)
    ('L3', 99152.0, 925, 1150),   # 第三层 下导线 (构件4)
]

def unit(c):
    dx, dy = c['b'][0]-c['a'][0], c['b'][1]-c['a'][1]
    L = math.hypot(dx, dy)
    return dx/L, dy/L, L

all_members = []
for tag, ca_z, y0, y1 in BANDS:
    segs = []
    for ln in d1['lines']:
        (xa, ya), (xb, yb) = ln['a'], ln['b']
        mx, my = (xa+xb)/2, (ya+yb)/2
        if not (100 <= mx <= 1150 and y0 <= my <= y1):
            continue
        L = math.dist(ln['a'], ln['b'])
        if L < 8: continue
        ang = math.degrees(math.atan2(yb-ya, xb-xa)) % 180
        segs.append({'a': [xa, ya], 'b': [xb, yb], 'len': L, 'ang': ang})
    # collinear clustering
    parent = list(range(len(segs)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    P = []
    for s in segs:
        ux, uy, L = unit(s)
        P.append((ux, uy, s['a'][0], s['a'][1], s['len']))
    def colin(i, j):
        uxi, uyi, axi, ayi, Li = P[i]
        uxj, uyj, axj, ayj, Lj = P[j]
        if abs(uxi*uxj + uyi*uyj) < 0.9985: return False
        perp = abs(uxj*(ayi-ayj) - uyj*(axi-axj))
        if perp > 2.0: return False
        t1 = (axj-axi)*uxi + (ayj-ayi)*uyi
        return (t1+Lj) > -4 and t1 < Li+4
    buckets = {}
    for i, s in enumerate(segs):
        buckets.setdefault(round(s['ang']/2.5), []).append(i)
    for key, idxs in buckets.items():
        for bi in range(len(idxs)):
            for bj in range(bi+1, len(idxs)):
                i, j = idxs[bi], idxs[bj]
                ri, rj = find(i), find(j)
                if ri != rj and colin(i, j): parent[rj] = ri
    groups = {}
    for i in range(len(segs)): groups.setdefault(find(i), []).append(i)
    axes = []
    for idxs in groups.values():
        uxi, uyi, ox, oy, _ = P[idxs[0]]
        if uxi < 0: uxi, uyi = -uxi, -uyi
        ts = []
        for i in idxs:
            for p in (segs[i]['a'], segs[i]['b']):
                ts.append((p[0]-ox)*uxi + (p[1]-oy)*uyi)
        t0, t1 = min(ts), max(ts)
        if t1-t0 < 30: continue
        a = [ox+uxi*t0, oy+uyi*t0]
        b = [ox+uxi*t1, oy+uyi*t1]
        axes.append({'a': a, 'b': b, 'ext': t1-t0, 'nseg': len(idxs)})
    print(f'{tag}: {len(segs)} segs -> {len(axes)} axes')
    # to 3D: front plane y=0
    cnt = 0
    for ax in axes:
        (xa, ya), (xb, yb) = ax['a'], ax['b']
        wx1, wz1 = (xa-CX)*SC, (Y_BOT-ya)*SC
        wx2, wz2 = (xb-CX)*SC, (Y_BOT-yb)*SC
        if math.dist([wx1,wz1],[wx2,wz2]) < 150: continue
        r = 90.0 if ax['ext'] > 150 else 45.0
        all_members.append({'mid': f'F{tag}_{cnt:03d}', 'role': f'横担{tag}(001正视图真实)',
                            'spec': '001正视图提取', 'r_mm': r,
                            'p1': [round(wx1,1), 0.0, round(wz1,1)],
                            'p2': [round(wx2,1), 0.0, round(wz2,1)]})
        cnt += 1
    print(f'  3D members: {cnt}')

json.dump({'members': all_members}, open('demo/crossarm001.json', 'w', encoding='utf-8'),
          ensure_ascii=False)
print('total:', len(all_members))
