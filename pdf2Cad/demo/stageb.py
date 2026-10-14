# -*- coding: utf-8 -*-
"""Stage B: extract real crossarm members from a detail sheet.
Pipeline: vectors -> OCR member table -> plan-view axes -> callout mapping.
Usage: python stageb.py 007"""
import fitz, json, sys, math, re
sys.stdout.reconfigure(encoding='utf-8')
from collections import defaultdict

SHEET = sys.argv[1] if len(sys.argv) > 1 else '007'
PDF = f'图纸/37-SA36901S-T0121-{SHEET}.pdf'
GLYPH_MAX, MIN_LINE = 20.0, 12.0

# ---------- 1. vector extraction ----------
doc = fitz.open(PDF)
page = doc[0]
lines, circles, glyph_contours = [], [], []
for p in page.get_drawings():
    r = p['rect']
    is_fill = p['fill'] is not None
    w = p.get('width') or 0
    segs, curves = [], []
    for item in p['items']:
        if item[0] == 'l':
            segs.append(([item[1].x, item[1].y], [item[2].x, item[2].y]))
        elif item[0] == 'c':
            curves.append([[pt.x, pt.y] for pt in item[1:]])
        elif item[0] == 're':
            rr = item[1]
            x0, y0, x1, y1 = rr.x0, rr.y0, rr.x1, rr.y1
            segs += [([x0,y0],[x1,y0]),([x1,y0],[x1,y1]),([x1,y1],[x0,y1]),([x0,y1],[x0,y0])]
        elif item[0] == 'qu':
            q = item[1]
            pts = [q.ul, q.ur, q.lr, q.ll, q.ul]
            for i in range(4):
                segs.append(([pts[i].x, pts[i].y], [pts[i+1].x, pts[i+1].y]))
    max_seg = max((math.dist(a,b) for a,b in segs), default=0)
    if r.width <= GLYPH_MAX and r.height <= GLYPH_MAX and (is_fill or len(segs) > 1 or max_seg < GLYPH_MAX*0.8):
        pts = []
        for a,b in segs:
            if not pts: pts.append(a)
            pts.append(b)
        if pts: glyph_contours.append({'pts': pts, 'bbox': [r.x0,r.y0,r.x1,r.y1]})
    else:
        for a,b in segs:
            if math.dist(a,b) >= MIN_LINE:
                lines.append({'a': a, 'b': b, 'w': w})
        if curves and r.width > GLYPH_MAX and abs(r.width-r.height) < max(r.width,r.height)*0.1:
            c = [(r.x0+r.x1)/2, (r.y0+r.y1)/2]
            rad = (r.width+r.height)/4
            if all(abs(math.dist(c,[x,y])-rad) < rad*0.25 for cv in curves for x,y in cv) and len(curves) <= 8:
                circles.append({'c': c, 'r': rad})
print(f'lines={len(lines)} circles={len(circles)}')

# glyph proximity grouping (for stats only)
GAP = 3.0
boxes = [g['bbox'] for g in glyph_contours]
n = len(boxes)
parent = list(range(n))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i
def ov(b1,b2):
    return not (b1[2]+GAP < b2[0] or b2[2]+GAP < b1[0] or b1[3]+GAP < b2[1] or b2[3]+GAP < b1[1])
cell = GAP*4
grid = {}
for i,b in enumerate(boxes):
    grid.setdefault((int(b[0]//cell), int(b[1]//cell)), []).append(i)
for i,b in enumerate(boxes):
    kx,ky = int(b[0]//cell), int(b[1]//cell)
    for dx in (-1,0,1):
        for dy in (-1,0,1):
            for j in grid.get((kx+dx,ky+dy), []):
                if j<=i: continue
                if ov(b, boxes[j]):
                    ri,rj = find(i), find(j)
                    if ri!=rj: parent[rj]=ri
groups = {}
for i in range(n): groups.setdefault(find(i), []).append(i)
print(f'glyph clusters={len(groups)}')
#doc.close()

# ---------- 2. OCR the member tables (right side) ----------
from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()
TB = fitz.Rect(1860, 30, 2395, 1200)
pix = page.get_pixmap(dpi=150, clip=TB)
pix.save(f'demo/s{SHEET}_table.png')
res, _ = ocr(f'demo/s{SHEET}_table.png')
titems = []
for box, text, conf in res:
    xs=[p[0] for p in box]; ys=[p[1] for p in box]
    titems.append({'text': text, 'conf': float(conf),
        'pt': [min(xs)*72/150+TB.x0, min(ys)*72/150+TB.y0,
               max(xs)*72/150+TB.x0, max(ys)*72/150+TB.y0]})
print(f'table OCR items={len(titems)}')

# cluster OCR items into rows by y
titems.sort(key=lambda t: t['pt'][1])
rows = []
for it in titems:
    yc = (it['pt'][1]+it['pt'][3])/2
    if rows and abs(yc - rows[-1]['yc']) < 7:
        rows[-1]['items'].append(it)
        n=len(rows[-1]['items'])
        rows[-1]['yc'] = rows[-1]['yc']*(n-1)/n + yc/n
    else:
        rows.append({'yc': yc, 'items': [it]})
print(f'table rows={len(rows)}')
for r in rows[:8]:
    print('  ', ' | '.join(i['text'] for i in sorted(r['items'], key=lambda t:t['pt'][0])))

json.dump({'lines': [{'a':l['a'],'b':l['b']} for l in lines],
           'circles': circles, 'table_rows': rows},
          open(f'demo/stageb_{SHEET}.json','w',encoding='utf-8'), ensure_ascii=False)
print(f'saved demo/stageb_{SHEET}.json')
