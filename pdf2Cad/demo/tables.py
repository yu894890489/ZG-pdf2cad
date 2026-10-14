# -*- coding: utf-8 -*-
"""Step 4: parse member detail table(s) from grid lines + OCR text."""
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('demo/data.json', encoding='utf-8'))
ocr = json.load(open('demo/ocr.json', encoding='utf-8'))['items']

# --- collect axis-aligned long lines in the table area (x>1900, y<780) ---
XR, YR = 1900, 780
hl, vl = [], []
for ln in data['lines']:
    (x0, y0), (x1, y1) = ln['a'], ln['b']
    if not (x0 > XR or y0 > YR):
        continue
    if abs(y0 - y1) < 0.5 and abs(x1 - x0) > 60:      # horizontal
        hl.append((min(x0, x1), y0, max(x0, x1)))
    elif abs(x0 - x1) < 0.5 and abs(y1 - y0) > 30:    # vertical
        vl.append((x0, min(y0, y1), max(y0, y1)))

# cluster h-lines by y (tolerance 1.5)
def cluster1d(vals, tol):
    vals = sorted(vals)
    out = [[vals[0]]]
    for v in vals[1:]:
        if v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [sum(g) / len(g) for g in out]

ys = cluster1d([h[1] for h in hl], 1.5)
xs = cluster1d([v[0] for v in vl], 1.5)
print('grid rows y:', [round(y, 1) for y in ys])
print('grid cols x:', [round(x, 1) for x in xs])

# --- map OCR items into cells ---
def cell_of(item):
    cx = (item['bbox'][0] + item['bbox'][2]) / 2
    cy = (item['bbox'][1] + item['bbox'][3]) / 2
    if not (xs[0] <= cx <= xs[-1] and ys[0] <= cy <= ys[-1]):
        return None
    ri = max(i for i, y in enumerate(ys) if y <= cy)
    ci = max(i for i, x in enumerate(xs) if x <= cx)
    return ri, ci

grid = {}
for item in ocr:
    c = cell_of(item)
    if c:
        grid.setdefault(c, []).append(item)

# --- assemble rows ---
rows = []
nrows = len(ys) - 1
ncols = len(xs) - 1
for ri in range(nrows):
    cells = []
    for ci in range(ncols):
        parts = grid.get((ri + 1, ci + 1), [])
        parts.sort(key=lambda i: i['bbox'][0])
        cells.append(' '.join(p['text'] for p in parts).strip())
    if any(cells):
        rows.append({'row_y': round((ys[ri] + ys[ri+1]) / 2, 1), 'cells': cells})

print(f'\ntable: {nrows} rows x {ncols} cols, {len(rows)} non-empty')
for r in rows:
    print(r['row_y'], r['cells'])

json.dump({'ys': ys, 'xs': xs, 'rows': rows}, open('demo/table.json', 'w', encoding='utf-8'),
          ensure_ascii=False, default=str)
