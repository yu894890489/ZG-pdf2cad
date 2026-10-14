# -*- coding: utf-8 -*-
"""Extract leg envelope polylines from 001 front view (authoritative leg shape)."""
import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')

d1 = json.load(open('demo/data001.json', encoding='utf-8'))
CX, Y_BOT, SC = 624.0, 3749.0, 135000.0/3632.0

# structural segments in the elevation region (exclude far-left dim lines x<230)
segs = []
for ln in d1['lines']:
    (xa, ya), (xb, yb) = ln['a'], ln['b']
    mx, my = (xa+xb)/2, (ya+yb)/2
    if not (230 <= mx <= 1100 and 90 <= my <= 3760):
        continue
    L = math.dist(ln['a'], ln['b'])
    if L < 6: continue
    segs.append((xa, ya, xb, yb, L))

# sample left/right outermost x per height band (every 30pt)
bands = {}
for xa, ya, xb, yb, L in segs:
    for x, y in ((xa, ya), (xb, yb)):
        k = round(y / 30)
        bands.setdefault(k, []).append((x, y))

left_pts, right_pts = [], []
for k in sorted(bands.keys()):
    pts = bands[k]
    xs = [p[0] for p in pts]
    ymid = sum(p[1] for p in pts) / len(pts)
    # leftmost / rightmost
    left_pts.append((min(xs), ymid))
    right_pts.append((max(xs), ymid))

def to_world(pts):
    return [[round((x-CX)*SC,1), round((Y_BOT-y)*SC,1)] for x,y in pts]

lw = to_world(left_pts)
rw = to_world(right_pts)
print('left leg envelope (x_mm, z_mm) sample:')
for p in lw[::max(1,len(lw)//15)]:
    print(f'  {p[0]:8.0f}  {p[1]:8.0f}')
print('right leg envelope sample:')
for p in rw[::max(1,len(rw)//15)]:
    print(f'  {p[0]:8.0f}  {p[1]:8.0f}')

json.dump({'left': lw, 'right': rw}, open('demo/legs.json','w'))
print('saved demo/legs.json')

# render to verify
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(6, 12))
for ln in d1['lines']:
    (xa, ya), (xb, yb) = ln['a'], ln['b']
    mx=(xa+xb)/2
    if not (230 <= mx <= 1100 and 90 <= (ya+yb)/2 <= 3760): continue
    ax.plot([(xa-CX)*SC,(xb-CX)*SC],[(Y_BOT-ya)*SC,(Y_BOT-yb)*SC],color='lightgray',lw=0.3)
ax.plot([p[0] for p in lw],[p[1] for p in lw],'r.-',ms=3,label='left')
ax.plot([p[0] for p in rw],[p[1] for p in rw],'b.-',ms=3,label='right')
ax.set_aspect('equal'); ax.legend(); ax.set_title('leg envelope')
plt.savefig('demo/legs_preview.png', dpi=80)
print('saved preview')
