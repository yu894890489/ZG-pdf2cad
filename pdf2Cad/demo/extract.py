# -*- coding: utf-8 -*-
"""Step 1: extract classified vector data from one drawing sheet."""
import fitz, json, sys, math
from collections import defaultdict

PDF = '图纸/37-SA36901S-T0121-050.pdf'
OUT = 'demo/data.json'

doc = fitz.open(PDF)
page = doc[0]

GLYPH_MAX = 20.0   # bbox size under which a path may be a text glyph
MIN_LINE = 12.0    # segment length to keep as a "geometry" line

lines = []      # {a:[x,y], b:[x,y], w:linewidth}
circles = []    # {c:[x,y], r, bbox}
arcs = []       # bezier curve chains (kept raw)
glyph_contours = []  # filled contours: {pts:[[x,y]...], bbox, hole:bool}

for p in page.get_drawings():
    r = p['rect']
    is_fill = p['fill'] is not None
    w = p.get('width') or 0
    # collect segments and curves per path
    segs = []
    curves = []
    for item in p['items']:
        if item[0] == 'l':
            p1, p2 = item[1], item[2]
            segs.append(([p1.x, p1.y], [p2.x, p2.y]))
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
    # glyph candidate: small bbox AND (filled OR drawn with short strokes)
    if small_box and (is_fill or len(segs) > 1 or max_seg < GLYPH_MAX * 0.8):
        pts = []
        for a, b in segs:
            if not pts: pts.append(a)
            pts.append(b)
        glyph_contours.append({'pts': pts, 'bbox': [r.x0, r.y0, r.x1, r.y1],
                               'n': len(pts)})
    else:
        for a, b in segs:
            if math.dist(a, b) >= MIN_LINE:
                lines.append({'a': a, 'b': b, 'w': w})
        # circle detection: 4+ closed curves, near-square bbox
        if curves and r.width > GLYPH_MAX and abs(r.width - r.height) < max(r.width, r.height) * 0.1:
            # estimate circle from bbox center
            c = [(r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2]
            rad = (r.width + r.height) / 4
            # only keep as circle if all curves stay near the circle
            ok = True
            for cv in curves:
                for x, y in cv:
                    d = abs(math.dist(c, [x, y]) - rad)
                    if d > rad * 0.25:
                        ok = False; break
                if not ok: break
            if ok and len(curves) <= 8:
                circles.append({'c': c, 'r': rad, 'bbox': [r.x0, r.y0, r.x1, r.y1],
                                'ncv': len(curves)})
            else:
                arcs.append({'curves': curves, 'bbox': [r.x0, r.y0, r.x1, r.y1]})
        elif curves:
            arcs.append({'curves': curves, 'bbox': [r.x0, r.y0, r.x1, r.y1]})

# group glyph contours into glyphs by bbox proximity (multi-stroke chars are
# side-by-side strokes, not nested) — merge while bbox gaps < GAP
GAP = 3.0
boxes = [list(g['bbox']) for g in glyph_contours]
parent = list(range(len(boxes)))

def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i

def overlap(b1, b2):
    return not (b1[2] + GAP < b2[0] or b2[2] + GAP < b1[0] or
                b1[3] + GAP < b2[1] or b2[3] + GAP < b1[1])

# sweep on x for candidate pairs (n is small enough to do O(n^2) safely here)
n = len(boxes)
for i in range(n):
    for j in range(i + 1, n):
        if overlap(boxes[i], boxes[j]):
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[rj] = ri

groups = {}
for i in range(n):
    groups.setdefault(find(i), []).append(i)
glyphs = []
for idxs in groups.values():
    bx = [min(boxes[i][0] for i in idxs), min(boxes[i][1] for i in idxs),
          max(boxes[i][2] for i in idxs), max(boxes[i][3] for i in idxs)]
    glyphs.append({'bbox': bx,
                   'contours': [glyph_contours[i]['pts'] for i in idxs]})

data = {'page': [page.rect.width, page.rect.height],
        'lines': lines, 'circles': circles, 'arcs': arcs, 'glyphs': glyphs}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(data, f)
print(f'lines={len(lines)} circles={len(circles)} arcs={len(arcs)} glyphs={len(glyphs)}')
print('page size:', page.rect.width, page.rect.height)
doc.close()
