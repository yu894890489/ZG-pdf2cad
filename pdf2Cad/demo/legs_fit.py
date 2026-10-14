# -*- coding: utf-8 -*-
"""Fit leg polylines from 001 front view body region (authoritative)."""
import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')

d1 = json.load(open('demo/data001.json', encoding='utf-8'))
CX, Y_BOT, SC = 624.0, 3749.0, 135000.0/3632.0

# structural segments in the BODY region (below lowest crossarm y>1050), exclude text/dims
segs = []
for ln in d1['lines']:
    (xa, ya), (xb, yb) = ln['a'], ln['b']
    mx, my = (xa+xb)/2, (ya+yb)/2
    if not (230 <= mx <= 1050 and 1050 <= my <= 3640):
        continue
    L = math.dist(ln['a'], ln['b'])
    if L < 6: continue
    segs.append((xa, ya, xb, yb, L))

# outermost x per height band (left/right of centerline)
bands = {}
for xa, ya, xb, yb, L in segs:
    for x, y in ((xa, ya), (xb, yb)):
        k = round(y / 25)
        bands.setdefault(k, []).append((x, y))

def envelope(side):
    pts = []
    for k in sorted(bands.keys()):
        pts_b = bands[k]
        xs = [p[0] for p in pts_b]
        ymid = sum(p[1] for p in pts_b) / len(pts_b)
        if side == 'L':
            cand = [x for x in xs if x < CX]
            if cand: pts.append((min(cand), ymid))
        else:
            cand = [x for x in xs if x > CX]
            if cand: pts.append((max(cand), ymid))
    return pts

Lp = envelope('L')
Rp = envelope('R')

# fit 2-segment polyline (kink search) via least squares on x as function of y
def fit2(pts, yk):
    import numpy as np
    a = [(y, x) for x, y in pts if y < yk]
    b = [(y, x) for x, y in pts if y >= yk]
    if len(a) < 3 or len(b) < 3: return None
    za = np.polyfit([p[0] for p in a], [p[1] for p in a], 1)
    zb = np.polyfit([p[0] for p in b], [p[1] for p in b], 1)
    return za, zb

import numpy as np
best = None
for yk in range(2900, 3400, 25):
    f = fit2(Lp, yk)
    if not f: continue
    # residual
    err = 0
    for x, y in Lp:
        z = f[0] if y < yk else f[1]
        err += (x - np.polyval(z, y)) ** 2
    if best is None or err < best[0]:
        best = (err, yk, f)
errL, ykL, fL = best
best = None
for yk in range(2900, 3400, 25):
    f = fit2(Rp, yk)
    if not f: continue
    err = 0
    for x, y in Rp:
        z = f[0] if y < yk else f[1]
        err += (x - np.polyval(z, y)) ** 2
    if best is None or err < best[0]:
        best = (err, yk, f)
errR, ykR, fR = best

def legline(f, yk, y0, y1):
    """polyline world coords: (x_mm, z_mm) at y0, yk, y1"""
    pts = [(y0, np.polyval(f[0], y0)), (yk, np.polyval(f[0], yk))]
    pts.append((y1, np.polyval(f[1], y1)))
    return [[round((x-CX)*SC,1), round((Y_BOT-y)*SC,1)] for y, x in pts]

legsL = legline(fL, ykL, 1050, 3630)
legsR = legline(fR, ykR, 1050, 3630)
print('left leg polyline (x_mm, z_mm):', legsL)
print('right leg polyline:', legsR)
print(f'kink at z≈{(Y_BOT-ykL)*SC:.0f}mm')
# half-widths at key heights
for zq in [0, 20000, 60000, 90000, 100000]:
    y = Y_BOT - zq/SC
    xl = np.polyval(fL[0] if y < ykL else fL[1], y)
    xr = np.polyval(fR[0] if y < ykR else fR[1], y)
    print(f'  z={zq:6d}: left x={xl:5.0f}({(xl-CX)*SC:+7.0f})  right x={xr:5.0f}({(xr-CX)*SC:+7.0f})  halfW={(xr-xl)/2*SC:.0f}')

json.dump({'left': legsL, 'right': legsR, 'kink_z': (Y_BOT-ykL)*SC,
           'fL': [list(fL[0]), list(fL[1])], 'fR': [list(fR[0]), list(fR[1])]},
          open('demo/legs_fit.json','w'))
print('saved')
