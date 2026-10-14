# -*- coding: utf-8 -*-
"""Stage B v2: rebuild 007 crossarm with correct semantics.
Main view = 俯视 right triangle (x,y). 单线图 = z profile. Scale from callout↔table."""
import json, sys, math, re
sys.stdout.reconfigure(encoding='utf-8')
import fitz
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

SHEET = '007'
PDF = f'图纸/37-SA36901S-T0121-{SHEET}.pdf'
d = json.load(open(f'demo/stageb_{SHEET}.json', encoding='utf-8'))
d2 = json.load(open(f'demo/stageb2_{SHEET}.json', encoding='utf-8'))
clusters, plan_circles = d2['clusters'], d2['plan_circles']
rows = d['table_rows']
ocr = RapidOCR()

# ---------- 1. table records via vertical grid lines ----------
doc = fitz.open(PDF); page = doc[0]
TBR = (1860, 30, 2395, 1250)
# vertical/horizontal grid lines within table region from vector data
vg, hg = [], []
for ln in d['lines']:
    (x0, y0), (x1, y1) = ln['a'], ln['b']
    if not (TBR[0] <= min(x0, x1) and max(x0, x1) <= TBR[2] and TBR[1] <= min(y0, y1) and max(y0, y1) <= TBR[3]):
        continue
    if abs(x0 - x1) < 0.6 and abs(y1 - y0) > 25:
        vg.append((x0, min(y0, y1), max(y0, y1)))
    elif abs(y0 - y1) < 0.6 and abs(x1 - x0) > 25:
        hg.append((y0, min(x0, x1), max(x0, x1)))
# cluster vertical lines into table-boundary columns (full-height ones)
vg.sort()
cols = []
for x, ya, yb in vg:
    if cols and abs(x - cols[-1][0]) < 4:
        cols[-1] = (cols[-1][0], min(cols[-1][1], ya), max(cols[-1][2], yb))
    else:
        cols.append((x, ya, yb))
# table boundary = columns with tall span
tall_cols = [c for c in cols if c[2] - c[1] > 300]
txs = sorted(set(round(c[0]) for c in tall_cols))
print('table vertical boundaries:', txs)
# group into 3 tables by x gaps > 60
tables = [[1862, 2012], [2015, 2395]]
print(f'tables: {len(tables)} x-ranges={[(t[0], t[-1]) for t in tables]}')

# assign OCR items to tables, then rows, then columns by boundary x
records = {}
for ti, t in enumerate(tables):
    titems = [it for it in sum([r['items'] for r in rows], [])
              if t[0] - 5 <= (it['pt'][0] + it['pt'][2]) / 2 <= t[-1] + 5]
    if not titems: continue
    titems.sort(key=lambda it: (it['pt'][1] + it['pt'][3]) / 2)
    rws = []
    for it in titems:
        yc = (it['pt'][1] + it['pt'][3]) / 2
        if rws and abs(yc - rws[-1]['yc']) < 7:
            rws[-1]['items'].append(it)
        else:
            rws.append({'yc': yc, 'items': [it]})
    for rw in rws:
        rw = rw['items']
        if len(rw) < 3: continue
        rw.sort(key=lambda it: it['pt'][0])
        texts = [it['text'] for it in rw]
        joined = ' '.join(texts)
        m = re.search(r'(\d{3,4})\s+(Q355[\d#X.\-]+|[0-9Xx.\-]+X[0-9Xx.\-]+|L\d+[Xx]\d+|FD\w+|C\d+\w*|U-?\d+|NUT-?\d+|GJ-?\d+|NX-?[\d.]+|JK-?\d+|-?\d+X\d+)\s+(\d{2,5})\s+(\d{1,2})\s+([\d.]+)\s+([\d.]+)', joined)
        if m:
            mid, spec, L, qty, uw, tw = m.groups()
            spec2 = (spec.replace('0219', 'φ219').replace('0245', 'φ245')
                         .replace('0194', 'φ194').replace('0273', 'φ273')
                         .replace('0355', 'Q355', 1) if spec.startswith('0355') else spec)
            records[mid] = {'spec': spec2, 'L': float(L), 'qty': int(qty),
                            'unit_w': float(uw), 'tbl': ti}
print(f'records: {len(records)}')
for k in list(records)[:8]: print('  ', k, records[k])

# ---------- 2. OCR callout circle numbers ----------
DPI = 300; Z = DPI / 72.0
pix = page.get_pixmap(dpi=DPI)
pimg = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
callouts = {}
for c in plan_circles:
    cx, cy = c['c'][0] * Z, c['c'][1] * Z
    r = max(c['r'] * Z * 1.6, 28)
    crop = pimg.crop((max(0, cx - r), max(0, cy - r), cx + r, cy + r))
    crop = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
    fp = 'demo/cc.png'; crop.save(fp)
    res, _ = ocr(fp)
    if res:
        txt = ''.join(t for _, t, _ in res).strip()
        txt = re.sub(r'[^0-9]', '', txt)
        cands = []
        if len(txt) in (3, 4):
            cands.append(txt)
            if len(txt) == 4: cands.append(txt[1:])   # 圆弧干扰: 去首位
        for cd in cands:
            callouts.setdefault(cd, []).append((c['c'][0], c['c'][1]))
print(f'callout numbers: {len(callouts)} -> {sorted(callouts.keys())}')

# ---------- 3. scale calibration: callout -> nearest axis -> L ----------
def dist_pt_seg(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy or 1
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + dx * t), py - (ay + dy * t))

scales = []
for num, poss in callouts.items():
    if num not in records: continue
    L = records[num]['L']
    for p in poss:
        best = min(clusters, key=lambda c: dist_pt_seg(p, c['a'], c['b']))
        dd = dist_pt_seg(p, best['a'], best['b'])
        if dd < 40 and best['ext'] > 40:
            s = L / best['ext']
            scales.append(s)
            print(f'  calib {num}: L={L} ext={best["ext"]:.0f}pt -> {s:.2f} mm/pt')
scales.sort()
# 主标定: 节间标注2870/2930/2360 <-> 提取270/280/230pt 及 表长5712<->561pt 均≈10.5
# 小板匹配(337/339)为误匹配(板真形/引线), 不采用
SCALE = 10.6
print(f'SCALE = {SCALE} mm/pt (web labels 2870/2930/2360 & tube 5712 consistent; small-plate matches rejected)')

# ---------- 4. z profile from 单线图 (1:150) ----------
SGL = (95, 70, 600, 300)
sg = []
for ln in d['lines']:
    (x0, y0), (x1, y1) = ln['a'], ln['b']
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    if SGL[0] <= mx <= SGL[2] and SGL[1] <= my <= SGL[3] and math.dist(ln['a'], ln['b']) > 60:
        sg.append(ln)
# top line = the long sloping one; bottom = horizontal
horiz = [ln for ln in sg if abs(ln['a'][1] - ln['b'][1]) < 3]
sloped = [ln for ln in sg if abs(ln['a'][1] - ln['b'][1]) >= 3]
hz = max(horiz, key=lambda ln: math.dist(ln['a'], ln['b'])) if horiz else None
sp = max(sloped, key=lambda ln: math.dist(ln['a'], ln['b'])) if sloped else None
print('single-line: horiz', hz and [round(v) for v in hz['a'] + hz['b']],
      'sloped', sp and [round(v) for v in sp['a'] + sp['b']])
S150 = 0.3528 * 150   # mm per pt at 1:150
def z_profile(xn):
    """xn in [0,1] along axis (0=root,1=tip) -> z mm above datum"""
    if not (hz and sp): return 0.0
    hx0, hx1 = min(hz['a'][0], hz['b'][0]), max(hz['a'][0], hz['b'][0])
    sx0, sx1 = min(sp['a'][0], sp['b'][0]), max(sp['a'][0], sp['b'][0])
    def yat(ln, x):
        x0, y0 = ln['a']; x1, y1 = ln['b']
        t = (x - x0) / (x1 - x0) if x1 != x0 else 0
        return y0 + t * (y1 - y0)
    # 单线图: 尖端(x=190,z=0) -> 根部(x=557,z=8674), 两段线性
    Z_ROOT = (293 - 129) * S150
    return Z_ROOT * xn

# ---------- 5. build 3D ----------
V = d2['clusters']
main_axes = [c for c in clusters if c['ext'] > 50
             and 60 <= c['a'][0] <= 1760 and 470 <= c['a'][1] <= 1290
             and 60 <= c['b'][0] <= 1760 and 470 <= c['b'][1] <= 1290]
# axis span along x -> normalize: root = max-x end? from overlay: tip top-left (small x), root bottom-right (large x)
xs_all = [c['a'][0] for c in main_axes] + [c['b'][0] for c in main_axes]
X_LO, X_HI = min(xs_all), max(xs_all)
print(f'main view x range: {X_LO:.0f}..{X_HI:.0f}')
Ys_all = [c['a'][1] for c in main_axes] + [c['b'][1] for c in main_axes]
Y_LO, Y_HI = min(Ys_all), max(Ys_all)

members = []
n = 0
for c in main_axes:
    (x1p, y1p), (x2p, y2p) = c['a'], c['b']
    n += 1
    # world x: root at X_HI, tip at X_LO
    wx1 = (X_HI - x1p) * SCALE
    wx2 = (X_HI - x2p) * SCALE
    # 立面图: 视图竖直方向 = 高度 z
    Y_BOT = 1349.0
    wz1 = (Y_BOT - y1p) * SCALE
    wz2 = (Y_BOT - y2p) * SCALE
    # 高度直接来自立面 y; 深度 y 用 ±650 收尖(050约定, 推定)
    z1, z2 = wz1, wz2
    t1 = max(0.0, min(1.0, (X_HI - x1p) / (X_HI - X_LO)))
    t2 = max(0.0, min(1.0, (X_HI - x2p) / (X_HI - X_LO)))
    wy1 = 650.0 * (1 - t1)
    wy2 = 650.0 * (1 - t2)
    ang = c['ang']
    is_h = ang < 4 or ang > 176
    steep = 30 < ang < 150
    role = '横担下弦' if is_h else ('横担斜弦' if (not steep and c['ext'] > 400) else
          ('腹杆' if steep else '横担连接件'))
    r = 105.0 if role in ('横担下弦', '横担斜弦') else 55.0
    # callout match
    rec = None
    best_num, best_d = None, 1e9
    for num, poss in callouts.items():
        if num not in records:
            continue
        for p in poss:
            dd = min(dist_pt_seg(p, c['a'], c['b']),
                     dist_pt_seg(p, c['b'], c['a']))
            if dd < best_d:
                best_d, best_num = dd, num
    if best_num and best_d < 45 and best_num in records:
        rec = {'id': best_num, **records[best_num]}
    members.append({'mid': f'S{n:03d}', 'role': role, 'r_mm': r, 'rec': rec or {},
                    'p1': [round(wx1, 1), round(wy1, 1), round(z1, 1)],
                    'p2': [round(wx2, 1), round(wy2, 1), round(z2, 1)],
                    'ang': ang, 'ext_pt': round(c['ext'])})

matched = sum(1 for m in members if m['rec'])
print(f'members: {len(members)}, with spec: {matched}')
for m in members:
    if m['rec']:
        print(f"  {m['mid']} #{m['rec']['id']} {m['rec']['spec']} L={m['rec']['L']} role={m['role']}")

json.dump({'members': members, 'records': records, 'scale': SCALE},
          open('demo/crossarm007_v2.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('saved demo/crossarm007_v2.json')
