# -*- coding: utf-8 -*-
"""Frame v3: extract ALL body members from 001 front view + crossarm bands.
Place on front/back faces (y=±hw), mirror to side faces. Authoritative front view."""
import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np

d1 = json.load(open('demo/data001.json', encoding='utf-8'))
lf = json.load(open('demo/legs_fit.json'))
ca = json.load(open('demo/crossarm001.json', encoding='utf-8'))
CX, Y_BOT, SC = 624.0, 3749.0, 135000.0/3632.0
Z_TOT = 135000.0
HW_BASE = 18780.0

fL = lf['fL']; yk = lf['kink_z']
def hw(z):
    if z < 4423:
        return HW_BASE + (13460.8 - HW_BASE) * (z / 4423.0)
    y = Y_BOT - z / SC
    za = fL[0] if z > yk else fL[1]
    return abs((np.polyval(za, y) - CX) * SC)

# ---------- extract body members from front view ----------
def to_xz(p):
    return ((p[0]-CX)*SC, (Y_BOT-p[1])*SC)

body = []   # list of (x1,z1,x2,z2, kind)
for ln in d1['lines']:
    (xa, ya), (xb, yb) = ln['a'], ln['b']
    mx, my = (xa+xb)/2, (ya+yb)/2
    if not (230 <= mx <= 1050 and 1050 <= my <= 3640):
        continue
    L = math.dist(ln['a'], ln['b'])
    if L < 20: continue
    ang = abs(math.degrees(math.atan2(yb-ya, xb-xa))) % 180
    x1, z1 = to_xz((xa, ya)); x2, z2 = to_xz((xb, yb))
    # keep only within body width envelope (avoid far stray)
    if abs(x1) > hw(max(z1,0))+500 or abs(x2) > hw(max(z2,0))+500:
        continue
    kind = 'H' if (ang < 6 or ang > 174) else ('V' if 84 < ang < 96 else 'D')
    body.append((x1, z1, x2, z2, kind))

print(f'body segments: {len(body)} (H={sum(1 for b in body if b[4]=="H")} D={sum(1 for b in body if b[4]=="D")} V={sum(1 for b in body if b[4]=="V")})')

# ---------- build 3D members ----------
members = []
def add(mid, spec, p1, p2, r, role):
    members.append({'mid': mid, 'spec': spec, 'role': role, 'r_mm': r,
                    'p1': [round(v,1) for v in p1], 'p2': [round(v,1) for v in p2]})

SIGNS = [(1,1),(-1,1),(-1,-1),(1,-1)]
R_LEG, R_BR = 180.0, 80.0

# legs: 4 legs along fitted profile (segmented every ~6m)
NSEG = 18
for si,(sx,sy) in enumerate(SIGNS):
    for i in range(NSEG):
        z0, z1 = Z_TOT*i/NSEG, Z_TOT*(i+1)/NSEG
        add(f'LEG{si}{i:02d}','主材', (sx*hw(z0), sy*hw(z0), z0), (sx*hw(z1), sy*hw(z1), z1), R_LEG, '塔身主材')

# body bracing: place extracted segments on 4 faces
cnt = 0
for x1, z1, x2, z2, kind in body:
    zc = (z1+z2)/2
    # scale x to leg hw at that z (drawn x is at front face width = 2*hw(z)/2=hw(z))
    # front face: y=-hw(z); the drawn x is along the face width
    # side faces: swap x->y
    for face in range(4):
        if face == 0:   # front y=-hw
            p1 = (x1, -hw(z1), z1); p2 = (x2, -hw(z2), z2)
        elif face == 1: # back y=+hw
            p1 = (x1, hw(z1), z1); p2 = (x2, hw(z2), z2)
        elif face == 2: # left x=-hw : use -x as the face width coordinate (y)
            p1 = (-hw(z1), -x1, z1); p2 = (-hw(z2), -x2, z2)
        else:           # right x=+hw
            p1 = (hw(z1), x1, z1); p2 = (hw(z2), x2, z2)
        r = R_BR if kind != 'V' else 100.0
        add(f'BR{cnt:03d}f{face}', '横隔' if kind=='H' else ('竖杆' if kind=='V' else '塔身斜材'),
            p1, p2, r, '横隔' if kind=='H' else ('竖杆' if kind=='V' else '塔身斜材'))
    cnt += 1

# crossarms from 001 front view (bands), ±325 front/back
for m in ca['members']:
    for syn, dy in ((1, -325.0), (-1, 325.0)):
        add('CA_'+m['mid'], m['role'], (m['p1'][0], dy, m['p1'][2]), (m['p2'][0], dy, m['p2'][2]), m['r_mm'], m['role'])

print(f'members: {len(members)}')
json.dump({'members': members}, open('demo/frame.json','w',encoding='utf-8'), ensure_ascii=False)

# SCAD
def scad_vec(p): return f"[{p[0]:.0f}, {p[1]:.0f}, {p[2]:.0f}]"
def color_of(mid):
    if mid.startswith('LEG'): return 'ForestGreen'
    if mid.startswith('BR'): return 'DarkOrange'
    if mid.startswith('CA'): return 'Crimson'
    return 'SteelBlue'
out = ['// SZK31102A 135m 双回路直线塔 — 框架v3 (001正视图全部塔身+横担提取)',
       '// 1:1 mm; Z向上; 根开37560(135m呼高), 总高135000',
       '// 塔身杆件=001正视图提取布置4面; 腿线=拟合; 横担=001正视图提取前后片±325',
       '$fn = 32;', '',
       'module tube(p1, p2, r, col) {',
       '  v = p2 - p1;  L = norm(v);  ax = cross([0,0,1], v);',
       '  translate(p1) color(col)',
       '    if (norm(ax) < 1e-9)',
       '      rotate([0, v[2] > 0 ? 0 : 180, 0]) cylinder(h = L, r = r);',
       '    else',
       '      rotate(a = acos(min(1, max(-1, v[2]/L))), v = ax) cylinder(h = L, r = r);',
       '}', '']
for m in members:
    out.append(f"// {m['role']} {m.get('spec','')}")
    out.append(f"tube({scad_vec(m['p1'])}, {scad_vec(m['p2'])}, {m['r_mm']:.0f}, \"{color_of(m['mid'])}\");")
    out.append('')
open('demo/tower_frame.scad','w',encoding='utf-8').write('\n'.join(out))
print('scad saved')
