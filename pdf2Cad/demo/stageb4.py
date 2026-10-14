# -*- coding: utf-8 -*-
"""Stage B step 4: assemble real-geometry crossarm from 007 and inject into frame.
Elevation axes = side-truss members (x, z). Plan axes = plan projection (x, y)."""
import json, sys, math, re
sys.stdout.reconfigure(encoding='utf-8')

SHEET = '007'
d = json.load(open(f'demo/stageb_{SHEET}.json', encoding='utf-8'))
d2 = json.load(open(f'demo/stageb2_{SHEET}.json', encoding='utf-8'))
d3 = json.load(open(f'demo/stageb3_{SHEET}.json', encoding='utf-8'))
clusters, plan_circles = d2['clusters'], d2['plan_circles']
rows = d['table_rows']

# ---------- parse member tables: split 3 parallel tables by x ----------
all_items = []
for r in rows:
    all_items.extend(r['items'])
# tables occupy ~3 bands; cluster item centers by x with gap>40pt
bands = []
for it in sorted(all_items, key=lambda t: (t['pt'][0]+t['pt'][2])/2):
    xc = (it['pt'][0]+it['pt'][2])/2
    if bands and xc - bands[-1]['xr'] < 45 and xc > bands[-1]['xr'] - 400:
        bands[-1]['items'].append(it)
        bands[-1]['xr'] = max(bands[-1]['xr'], xc)
    else:
        bands.append({'xr': xc, 'items': [it]})
bands = [b for b in bands if len(b['items']) > 15]
print(f'table bands: {len(bands)} widths={[len(b["items"]) for b in bands]}')

recs = {}
for bi, b in enumerate(bands):
    items = sorted(b['items'], key=lambda t: (t['pt'][1]+t['pt'][3])/2)
    rws = []
    for it in items:
        yc = (it['pt'][1]+it['pt'][3])/2
        if rws and abs(yc - rws[-1]['yc']) < 7:
            rws[-1]['items'].append(it)
        else:
            rws.append({'yc': yc, 'items': [it]})
    for rw in rws:
        texts = [i['text'] for i in sorted(rw['items'], key=lambda t: t['pt'][0])]
        joined = ' '.join(texts)
        m = re.search(r'(\d{3,4})\s+(Q355[\d#X.\-]+|[\dXx.\-]+X[\dXx.\-]+|L\d+[Xx]\d+)\s+(\d{2,5})\s+(\d{1,2})\s+([\d.]+)\s+([\d.]+)', joined)
        if m:
            mid, spec, L, qty, uw, tw = m.groups()
            spec2 = spec.replace('0219', 'φ219').replace('0245', 'φ245').replace('0273','φ273').replace('0194','φ194')
            recs[mid] = {'spec': spec2, 'L': float(L), 'qty': int(qty), 'unit_w': float(uw)}
print(f'parsed records: {len(recs)}')
for k in list(recs)[:5]: print('  ', k, recs[k])

# ---------- regions ----------
ELE = (120, 760, 1370, 1420)
PLA = (1370, 940, 2300, 1430)
SCALE_MM = 12.49          # mm per pt (tip-to-tip 23000mm over 1841pt)
X0, Y0 = 231.0, 1349.0    # elevation origin: bottom-chord left end

def in_reg(c, reg):
    return reg[0] <= c[0] <= reg[2] and reg[1] <= c[1] <= reg[3]

ele_axes = [c for c in clusters if in_reg([(c['a'][0]+c['b'][0])/2, (c['a'][1]+c['b'][1])/2], ELE)
            and c['ext'] > 100]
pla_axes = [c for c in clusters if in_reg([(c['a'][0]+c['b'][0])/2, (c['a'][1]+c['b'][1])/2], PLA)
            and c['ext'] > 60 and not (c['ang'] < 2 and c['ext'] < 700 and abs(c['a'][1]-c['b'][1]) < 1 and c['nseg'] >= 2 and c['gap'] > 14)]
print(f'elevation axes: {len(ele_axes)}, plan axes: {len(pla_axes)}')

# ---------- callout circles -> records ----------
def circle_label(c):
    return None
# OCR numbers inside circles was not run per-circle; map circles to nearest table id by position later.
# For now: attach record ids in plan order by matching circle count to member count is unsafe;
# instead we attach specs by member LENGTH match where possible.

# ---------- build 3D members ----------
Y_TAPER = 650.0   # root half-spacing of side planes
members = []
mid_n = 0
def add(p1, p2, r, role, rec=None):
    global mid_n
    mid_n += 1
    members.append({'mid': f'R{mid_n:03d}', 'p1': [round(v,1) for v in p1],
                    'p2': [round(v,1) for v in p2], 'r_mm': r, 'role': role,
                    'rec': rec or {}})

# elevation side truss (front plane y=yv(t) tapering; mirror for back)
# z = (Y0 - y_pt) * SCALE_MM ; x_mm = (x_pt - X0) * SCALE_MM
# plan taper: side plane y at position x: linear 650 -> 0 across the truss x-span
EX0, EX1 = 231.0, 2072.0   # elevation x extent (pt)
def y_taper(x_pt):
    t = max(0.0, min(1.0, (x_pt - EX0) / (EX1 - EX0)))
    return Y_TAPER * (1 - t)

R_MAIN, R_WEB, R_PLN = 110.0, 60.0, 50.0
used_recs = set()
for c in ele_axes:
    (x1p, y1p), (x2p, y2p) = c['a'], c['b']
    z1 = (Y0 - y1p) * SCALE_MM
    z2 = (Y0 - y2p) * SCALE_MM
    x1 = (x1p - X0) * SCALE_MM
    x2 = (x2p - X0) * SCALE_MM
    ang = c['ang']
    steep = 25 < ang < 155
    is_horiz = ang < 3 or ang > 177
    if is_horiz:
        role, r = '下弦(真实几何)', R_MAIN
    elif steep and c['ext'] > 300:
        role, r = '顶弦(真实几何)', R_MAIN
    else:
        role, r = '腹杆(真实几何)', R_WEB
    for syn in (1, -1):
        yv1 = syn * y_taper(x1p)
        yv2 = syn * y_taper(x2p)
        add((x1, yv1, z1), (x2, yv2, z2), r, role)
# transverse frames from elevation verticals (short steep segments) — one per pair
steep_short = [c for c in ele_axes if 60 < c['ang'] < 120 and c['ext'] <= 300]
for c in steep_short:
    (x1p, y1p), (x2p, y2p) = c['a'], c['b']
    x1 = (x1p - X0) * SCALE_MM
    x2 = (x2p - X0) * SCALE_MM
    z1 = (Y0 - y1p) * SCALE_MM
    z2 = (Y0 - y2p) * SCALE_MM
    yw = y_taper((x1p+x2p)/2)
    add((x1, yw, z1), (x2, -yw, z2) if abs(z1-z2) < 5 else (x2, yw*0.0, z2), R_WEB, '横隔(真实几何)')

# plan members: transverse + plan diagonals (excluding table grid rows)
for c in pla_axes:
    (x1p, y1p), (x2p, y2p) = c['a'], c['b']
    x1 = (x1p - EX0) * SCALE_MM
    x2 = (x2p - EX0) * SCALE_MM
    # plan y -> world y: plan view center line = world y 0; ±taper bounds
    # normalize by the plan view's vertical center (~y 1140pt)
    PC = 1140.0
    y1w = -(y1p - PC) * SCALE_MM
    y2w = -(y2p - PC) * SCALE_MM
    add((x1, y1w, 0.0), (x2, y2w, 0.0), R_PLN, '平面杆件(真实几何)')

print(f'crossarm members built: {len(members)}')
xs = [m['p1'][0] for m in members] + [m['p2'][0] for m in members]
zs = [m['p1'][2] for m in members] + [m['p2'][2] for m in members]
print(f'x range: {min(xs):.0f}..{max(xs):.0f}  z range: {min(zs):.0f}..{max(zs):.0f}')

json.dump({'members': members, 'records': recs, 'scale': SCALE_MM},
          open('demo/crossarm007.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('saved demo/crossarm007.json')
