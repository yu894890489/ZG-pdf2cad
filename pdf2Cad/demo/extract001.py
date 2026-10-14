# -*- coding: utf-8 -*-
"""001 total drawing: extract geometry for tower frame reconstruction."""
import fitz, json, sys, math
sys.stdout.reconfigure(encoding='utf-8')

PDF = '图纸/37-SA36901S-T0121-001.pdf'
doc = fitz.open(PDF)
page = doc[0]
paths = page.get_drawings()
print('paths:', len(paths))

GLYPH_MAX = 20.0
MIN_LINE = 12.0
lines, circles, glyph_contours, arcs = [], [], [], []
for p in paths:
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
            segs.append(([x0, y0], [x1, y0])); segs.append(([x1, y0], [x1, y1]))
            segs.append(([x1, y1], [x0, y1])); segs.append(([x0, y1], [x0, y0]))
        elif item[0] == 'qu':
            q = item[1]
            pts = [q.ul, q.ur, q.lr, q.ll, q.ul]
            for i in range(4):
                segs.append(([pts[i].x, pts[i].y], [pts[i+1].x, pts[i+1].y]))
    max_seg = max((math.dist(a, b) for a, b in segs), default=0)
    small_box = r.width <= GLYPH_MAX and r.height <= GLYPH_MAX
    if small_box and (is_fill or len(segs) > 1 or max_seg < GLYPH_MAX * 0.8):
        pts = []
        for a, b in segs:
            if not pts: pts.append(a)
            pts.append(b)
        if pts:
            glyph_contours.append({'pts': pts, 'bbox': [r.x0, r.y0, r.x1, r.y1]})
    else:
        for a, b in segs:
            if math.dist(a, b) >= MIN_LINE:
                lines.append({'a': a, 'b': b, 'w': w})
        if curves and r.width > GLYPH_MAX and abs(r.width - r.height) < max(r.width, r.height) * 0.1:
            c = [(r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2]
            rad = (r.width + r.height) / 4
            ok = all(abs(math.dist(c, [x, y]) - rad) < rad * 0.25
                     for cv in curves for x, y in cv) and len(curves) <= 8
            if ok:
                circles.append({'c': c, 'r': rad, 'bbox': [r.x0, r.y0, r.x1, r.y1]})
            else:
                arcs.append({'curves': curves, 'bbox': [r.x0, r.y0, r.x1, r.y1]})
        elif curves:
            arcs.append({'curves': curves, 'bbox': [r.x0, r.y0, r.x1, r.y1]})

# glyph grouping (proximity merge)
GAP = 3.0
boxes = [g['bbox'] for g in glyph_contours]
n = len(boxes)
parent = list(range(n))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i
def overlap(b1, b2):
    return not (b1[2] + GAP < b2[0] or b2[2] + GAP < b1[0] or
                b1[3] + GAP < b2[1] or b2[3] + GAP < b1[1])
cell = GAP * 4
grid = {}
for i, b in enumerate(boxes):
    grid.setdefault((int(b[0] // cell), int(b[1] // cell)), []).append(i)
for i, b in enumerate(boxes):
    kx, ky = int(b[0] // cell), int(b[1] // cell)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for j in grid.get((kx + dx, ky + dy), []):
                if j <= i: continue
                if overlap(b, boxes[j]):
                    ri, rj = find(i), find(j)
                    if ri != rj: parent[rj] = ri
groups = {}
for i in range(n):
    groups.setdefault(find(i), []).append(i)
glyphs = []
for idxs in groups.values():
    bx = [min(boxes[i][0] for i in idxs), min(boxes[i][1] for i in idxs),
          max(boxes[i][2] for i in idxs), max(boxes[i][3] for i in idxs)]
    glyphs.append({'bbox': bx, 'contours': [glyph_contours[i]['pts'] for i in idxs]})

data = {'page': [page.rect.width, page.rect.height],
        'lines': lines, 'circles': circles, 'arcs': arcs, 'glyphs': glyphs}
json.dump(data, open('demo/data001.json', 'w', encoding='utf-8'))
print(f'lines={len(lines)} circles={len(circles)} arcs={len(arcs)} glyphs={len(glyphs)}')
doc.close()
