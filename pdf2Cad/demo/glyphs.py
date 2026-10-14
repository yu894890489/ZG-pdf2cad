# -*- coding: utf-8 -*-
"""Step 2: cluster vector text into runs by baseline, signature whole runs,
render unique ones for manual labeling."""
import json, sys, math, hashlib
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw, ImageFont

data = json.load(open('demo/data.json', encoding='utf-8'))

# ---- flatten to dashes (each original path = one dash contour) ----
dashes = []
for g in data['glyphs']:
    for pts in g['contours']:
        if len(pts) < 2:
            continue
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        b = [min(xs), min(ys), max(xs), max(ys)]
        if b[3] - b[1] > 16 or b[2] - b[0] > 16:   # graphics, not text
            continue
        dashes.append({'pts': pts, 'bbox': b})
print(f'text dashes: {len(dashes)}')

# ---- cluster dashes into text lines by y-center ----
Y_TOL = 2.2
dashes.sort(key=lambda d: (d['bbox'][1] + d['bbox'][3]) / 2)
lines = []
for d in dashes:
    yc = (d['bbox'][1] + d['bbox'][3]) / 2
    placed = False
    for L in lines:
        if abs(yc - L['yc']) <= Y_TOL:
            L['dashes'].append(d)
            n = len(L['dashes'])
            L['yc'] = L['yc'] * (n-1) / n + yc / n
            placed = True
            break
    if not placed:
        lines.append({'yc': yc, 'dashes': [d]})
print(f'text lines: {len(lines)}')

# ---- split lines into runs at x gaps ----
SPLIT_GAP = 11.0
runs = []
for L in lines:
    ds = sorted(L['dashes'], key=lambda d: d['bbox'][0])
    cur = [ds[0]]
    for d in ds[1:]:
        prev = cur[-1]
        if d['bbox'][0] - prev['bbox'][2] > SPLIT_GAP:
            runs.append(cur); cur = [d]
        else:
            cur.append(d)
    runs.append(cur)

# ---- signature per run ----
def run_sig(rs):
    x0 = min(d['bbox'][0] for d in rs); y0 = min(d['bbox'][1] for d in rs)
    x1 = max(d['bbox'][2] for d in rs); y1 = max(d['bbox'][3] for d in rs)
    w = x1 - x0; h = y1 - y0
    m = max(w, h, 1e-6)
    items = []
    for d in rs:
        b = d['bbox']
        cx = round((b[0] + b[2] - 2*x0) / m * 200) / 2
        cy = round((b[1] + b[3] - 2*y0) / m * 200) / 2
        dw = round((b[2] - b[0]) / m * 100)
        dh = round((b[3] - b[1]) / m * 100)
        items.append((cx, cy, dw, dh, len(d['pts'])))
    items.sort()
    return hashlib.md5(repr(items).encode()).hexdigest()[:12], [x0, y0, x1, y1]

run_data = []
for rs in runs:
    sig, bbox = run_sig(rs)
    h = bbox[3] - bbox[1]
    run_data.append({'sig': sig, 'bbox': bbox, 'nd': len(rs), 'h': round(h, 1)})

uniq = {}
for r in run_data:
    uniq.setdefault(r['sig'], []).append(r)
print(f'runs: {len(run_data)}, unique sigs: {len(uniq)}')

# ---- render contact sheets of unique runs ----
DPI = 300
Z = DPI / 72.0
import fitz
doc = fitz.open('图纸/37-SA36901S-T0121-050.pdf')
page = doc[0]
pix = page.get_pixmap(dpi=DPI)
page_img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
doc.close()

sigs = sorted(uniq.keys(), key=lambda s: -len(uniq[s]))
COLS = 5
CELL_W, CELL_H = 300, 40
ROWS = 16
per_sheet = COLS * ROWS
font = ImageFont.load_default()
nsheets = (len(sigs) + per_sheet - 1) // per_sheet
for si in range(0, len(sigs), per_sheet):
    batch = sigs[si:si+per_sheet]
    sheet = Image.new('RGB', (COLS*CELL_W, ROWS*CELL_H), 'white')
    d = ImageDraw.Draw(sheet)
    for k, s in enumerate(batch):
        b = uniq[s][0]['bbox']
        pad = 3
        crop = page_img.crop((max(int(b[0]*Z)-pad, 0), max(int(b[1]*Z)-pad, 0),
                              int(b[2]*Z)+pad, int(b[3]*Z)+pad))
        if crop.width > CELL_W - 60:
            ratio = (CELL_W - 60) / crop.width
            crop = crop.resize((CELL_W - 60, max(1, int(crop.height * ratio))))
        cx = (k % COLS) * CELL_W; cy = (k // COLS) * CELL_H
        sheet.paste(crop, (cx + 55, cy + (CELL_H - crop.height) // 2))
        d.text((cx + 3, cy + 12), s, fill='red', font=font)
        d.rectangle([cx, cy, cx + CELL_W - 1, cy + CELL_H - 1], outline=(210, 210, 210))
    sheet.save(f'demo/run_sheet_{si//per_sheet:02d}.png')

json.dump(run_data, open('demo/runs.json', 'w'), ensure_ascii=False)
json.dump({s: len(uniq[s]) for s in sigs}, open('demo/sig_counts.json', 'w'))
print(f'contact sheets: {nsheets} -> demo/run_sheet_XX.png')
