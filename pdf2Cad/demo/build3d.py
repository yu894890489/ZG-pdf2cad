# -*- coding: utf-8 -*-
"""Step 5: reconstruct 3D stick model of the X-joint cluster from extracted lines."""
import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('demo/data.json', encoding='utf-8'))
table = json.load(open('demo/table.json', encoding='utf-8'))

# ---- region of the 1:40 X-brace detail (tune by inspection) ----
RX0, RY0, RX1, RY1 = 950, 540, 2000, 1300

lines = []
for ln in data['lines']:
    (x0, y0), (x1, y1) = ln['a'], ln['b']
    if RX0 <= min(x0, x1) and max(x0, x1) <= RX1 and RY0 <= min(y0, y1) and max(y0, y1) <= RY1:
        L = math.dist(ln['a'], ln['b'])
        if L > 60:
            ang = math.degrees(math.atan2(abs(y1 - y0), abs(x1 - x0)))
            lines.append({'a': ln['a'], 'b': ln['b'], 'len': L, 'ang': ang,
                          'vert': ang > 80, 'horiz': ang < 10, 'diag': 10 <= ang <= 80})

verts = sorted([l for l in lines if l['vert']], key=lambda l: -l['len'])
horizs = sorted([l for l in lines if l['horiz']], key=lambda l: -l['len'])
diags = sorted([l for l in lines if l['diag']], key=lambda l: -l['len'])
print(f'region lines: vert={len(verts)} horiz={len(horizs)} diag={len(diags)}')
print('top verticals:')
for l in verts[:8]:
    print(f"  ({l['a'][0]:.0f},{l['a'][1]:.0f})-({l['b'][0]:.0f},{l['b'][1]:.0f}) len={l['len']:.0f}")
print('top horizontals:')
for l in horizs[:8]:
    print(f"  ({l['a'][0]:.0f},{l['a'][1]:.0f})-({l['b'][0]:.0f},{l['b'][1]:.0f}) len={l['len']:.0f}")
print('top diagonals:')
for l in diags[:8]:
    print(f"  ({l['a'][0]:.0f},{l['a'][1]:.0f})-({l['b'][0]:.0f},{l['b'][1]:.0f}) len={l['len']:.0f} ang={l['ang']:.1f}")

# ---- pair parallel outlines into tube members ----
def pair_and_axis(cands, want_angle):
    """group near-parallel, near-collinear-ish pairs -> axis line"""
    used = [False] * len(cands)
    axes = []
    for i, l1 in enumerate(cands):
        if used[i]: continue
        for j in range(i + 1, len(cands)):
            l2 = cands[j]
            if used[j]: continue
            # parallel and offset less than 60pt
            d = abs(l1['ang'] - l2['ang'])
            if d > 3: continue
            # distance between midpoints projected perpendicular
            m1 = ((l1['a'][0] + l1['b'][0]) / 2, (l1['a'][1] + l1['b'][1]) / 2)
            m2 = ((l2['a'][0] + l2['b'][0]) / 2, (l2['a'][1] + l2['b'][1]) / 2)
            if math.dist(m1, m2) > 400: continue
            # perpendicular offset of l2 midpoint from l1 line
            ax, ay = l1['a']; bx, by = l1['b']
            L = math.dist(l1['a'], l1['b'])
            off = abs((bx - ax) * (m1[1] - ay) - (by - ay) * (m1[0] - ax)) / L
            if off > 60: continue
            used[i] = used[j] = True
            p1 = ((l1['a'][0] + l2['a'][0]) / 2, (l1['a'][1] + l2['a'][1]) / 2)
            p2 = ((l1['b'][0] + l2['b'][0]) / 2, (l1['b'][1] + l2['b'][1]) / 2)
            # axis endpoints = extremes of the two lines projected on axis dir
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            n = math.hypot(dx, dy) or 1
            dx, dy = dx / n, dy / n
            pts = [l1['a'], l1['b'], l2['a'], l2['b']]
            ts = [(p[0] - p1[0]) * dx + (p[1] - p1[1]) * dy for p in pts]
            t0, t1 = min(ts), max(ts)
            axes.append({'a': [p1[0] + dx * t0, p1[1] + dy * t0],
                         'b': [p1[0] + dx * t1, p1[1] + dy * t1],
                         'off': off, 'len': t1 - t0})
            break
        # unpaired long line also kept (single edge -> axis guess)
    return axes

v_axes = pair_and_axis(verts, 'v')
h_axes = pair_and_axis(horizs, 'h')
d_axes = pair_and_axis(diags, 'd')
print(f'\npaired axes: vert={len(v_axes)} horiz={len(h_axes)} diag={len(d_axes)}')
for name, arr in (('V', v_axes), ('H', h_axes), ('D', d_axes)):
    for a in arr:
        print(f" {name} ({a['a'][0]:.0f},{a['a'][1]:.0f})-({a['b'][0]:.0f},{a['b'][1]:.0f}) off={a['off']:.1f} len={a['len']:.0f}")

json.dump({'v': v_axes, 'h': h_axes, 'd': d_axes},
          open('demo/axes.json', 'w'), ensure_ascii=False)
