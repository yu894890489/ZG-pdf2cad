# -*- coding: utf-8 -*-
"""Stage B step 3: assemble 007 crossarm 3D from elevation(W, x-z) + plan(x-y) views.
Inject into frame at z=114297 replacing parametric level-2 crossarm."""
import json, sys, math, re
sys.stdout.reconfigure(encoding='utf-8')

SHEET = '007'
d = json.load(open(f'demo/stageb_{SHEET}.json', encoding='utf-8'))
d2 = json.load(open(f'demo/stageb2_{SHEET}.json', encoding='utf-8'))
lines, circles = d['lines'], d['circles']
clusters, plan_circles = d2['clusters'], d2['plan_circles']
rows = d['table_rows']

# table rows -> records: {id, spec, length, qty, unit_w, total_w}
recs = {}
for r in rows:
    items = sorted(r['items'], key=lambda t: t['pt'][0])
    texts = [i['text'] for i in items]
    joined = ' '.join(texts)
    m = re.match(r'^\s*(\d{3,4})\s+(Q355[0-9#X.\-]+|L?\d+X\d+|\d+X\d+|L\d+[*X]\d+)\s+(\d{2,5})\s+(\d{1,2})\s+([\d.]+)\s+([\d.]+)', joined)
    if m:
        mid, spec, L, qty, uw, tw = m.groups()
        recs[mid] = {'spec': spec.replace('0219', 'φ219').replace('0245', 'φ245'),
                     'L': float(L), 'qty': int(qty), 'unit_w': float(uw)}
print(f'table records: {len(recs)}')
sample = list(recs.items())[:6]
for k, v in sample: print('  ', k, v)

ELE = (120, 620, 1363, 1450)   # elevation view region (x-z)
PLA = (1363, 620, 2300, 1450)  # plan view region (x-y)

def in_reg(c, reg):
    return reg[0] <= c[0] <= reg[2] and reg[1] <= c[1] <= reg[3]

# ---------- elevation: cluster axes in ELE, keep long ones ----------
ele_axes = [c for c in clusters if in_reg([(c['a'][0]+c['b'][0])/2, (c['a'][1]+c['b'][1])/2], ELE)]
print(f'elevation axes: {len(ele_axes)}')
for c in sorted(ele_axes, key=lambda c: -c['ext'])[:14]:
    print(f"  ({c['a'][0]:.0f},{c['a'][1]:.0f})-({c['b'][0]:.0f},{c['b'][1]:.0f}) ext={c['ext']:.0f} ang={c['ang']}")

# ---------- plan axes ----------
pla_axes = [c for c in clusters if in_reg([(c['a'][0]+c['b'][0])/2, (c['a'][1]+c['b'][1])/2], PLA)]
print(f'plan axes: {len(pla_axes)}')
for c in sorted(pla_axes, key=lambda c: -c['ext'])[:14]:
    print(f"  ({c['a'][0]:.0f},{c['a'][1]:.0f})-({c['b'][0]:.0f},{c['b'][1]:.0f}) ext={c['ext']:.0f} ang={c['ang']}")

json.dump({'ele_axes': ele_axes, 'pla_axes': pla_axes, 'records': recs},
          open(f'demo/stageb3_{SHEET}.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('saved demo/stageb3_007.json')
