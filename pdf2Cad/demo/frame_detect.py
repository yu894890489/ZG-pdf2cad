# -*- coding: utf-8 -*-
"""Detect tower frame geometry from 001 elevation: legs, panels, crossarms."""
import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('demo/data001.json', encoding='utf-8'))
RX0, RY0, RX1, RY1 = 60, 90, 1010, 3740   # elevation region

segs = []
for ln in data['lines']:
    (x0, y0), (x1, y1) = ln['a'], ln['b']
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    if not (RX0 <= mx <= RX1 and RY0 <= my <= RY1):
        continue
    L = math.dist(ln['a'], ln['b'])
    if L < 20:
        continue
    ang = math.degrees(math.atan2(abs(y1 - y0), abs(x1 - x0)))
    kind = 'V' if ang > 80 else ('H' if ang < 5 else 'D')
    segs.append({'a': [x0, y0], 'b': [x1, y1], 'len': L, 'kind': kind})

H = sorted([s for s in segs if s['kind'] == 'H'], key=lambda s: -s['len'])
D = sorted([s for s in segs if s['kind'] == 'D'], key=lambda s: -s['len'])
V = sorted([s for s in segs if s['kind'] == 'V'], key=lambda s: -s['len'])
print(f'H={len(H)} D={len(D)} V={len(V)}')
print('\n-- longest horizontals (panels/crossarms) --')
for s in H[:25]:
    print(f"  ({s['a'][0]:6.0f},{s['a'][1]:6.0f})-({s['b'][0]:6.0f},{s['b'][1]:6.0f}) len={s['len']:6.0f}")
print('\n-- longest diagonals (legs/bracing) --')
for s in D[:15]:
    print(f"  ({s['a'][0]:6.0f},{s['a'][1]:6.0f})-({s['b'][0]:6.0f},{s['b'][1]:6.0f}) len={s['len']:6.0f}")
print('\n-- longest verticals --')
for s in V[:10]:
    print(f"  ({s['a'][0]:6.0f},{s['a'][1]:6.0f})-({s['b'][0]:6.0f},{s['b'][1]:6.0f}) len={s['len']:6.0f}")
json.dump(segs, open('demo/elev_segs.json', 'w'))
