# -*- coding: utf-8 -*-
"""Frame v2: fitted legs from 001 front view + panel levels + 001-extracted crossarms + base splay."""
import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np

d1 = json.load(open('demo/data001.json', encoding='utf-8'))
lf = json.load(open('demo/legs_fit.json'))
ca = json.load(open('demo/crossarm001.json', encoding='utf-8'))
CX, Y_BOT, SC = 624.0, 3749.0, 135000.0/3632.0
Z_TOT = 135000.0
HW_BASE = 18780.0   # 根开/2 (135m variant)

# leg half-width function from fitted lines (use left fit, mirrored; base extended)
fL = lf['fL']; yk = lf['kink_z']
def hw(z):
    y = Y_BOT - z / SC
    if z < 4423:
        # below the fit: extend to base
        return HW_BASE + (13460.8 - HW_BASE) * (z / 4423.0)
    za = fL[0] if z > lf['kink_z'] else fL[1]
    x = np.polyval(za, y)
    return abs((x - CX) * SC)

# panel levels: horizontal members in body region spanning >40% of local leg spacing
segs = []
for ln in d1['lines']:
    (xa, ya), (xb, yb) = ln['a'], ln['b']
    mx, my = (xa+xb)/2, (ya+yb)/2
    if not (230 <= mx <= 1050 and 1050 <= my <= 3640):
        continue
    if abs(ya-yb) < 1.5 and abs(xa-xb) > 30:
        segs.append((min(xa,xb), my, max(xa,xb)))
# cluster by y
levels = []
for x0, y, x1 in sorted(segs, key=lambda s: s[1]):
    span = (x1-x0)*SC
    z = (Y_BOT-y)*SC
    if span > 0.4 * 2*hw(z):
        if levels and abs(levels[-1][0]-z) < 400:
            continue
        levels.append((z, span))
levels.sort()
print('panel levels (z, span):')
for z, sp in levels:
    print(f'  z={z:8.0f}  span={sp:7.0f}')

# build members
members = []
def add(mid, spec, p1, p2, r, role):
    members.append({'mid': mid, 'spec': spec, 'role': role, 'r_mm': r,
                    'p1': [round(v,1) for v in p1], 'p2': [round(v,1) for v in p2]})

R_LEG, R_BR = 180.0, 80.0
SIGNS = [(1,1),(-1,1),(-1,-1),(1,-1)]
# panel z list: base + detected + top
panel_z = sorted(set([0.0, 4423.0] + [z for z,_ in levels if z > 4423] + [Z_TOT]))
panel_z = [z for z in panel_z if 0 <= z <= Z_TOT]
print(f'panels: {len(panel_z)-1}')

# legs: polyline through panel levels
for si,(sx,sy) in enumerate(SIGNS):
    for i in range(len(panel_z)-1):
        z0,z1 = panel_z[i], panel_z[i+1]
        add(f'LEG{si}{i:02d}','主材(001腿线拟合)',
            (sx*hw(z0), sy*hw(z0), z0), (sx*hw(z1), sy*hw(z1), z1), R_LEG, '塔身主材分段')

# per panel: diaphragm + X bracing on 4 faces
for pi in range(len(panel_z)-1):
    z0,z1 = panel_z[pi], panel_z[pi+1]
    c0 = [(sx*hw(z0), sy*hw(z0), z0) for sx,sy in SIGNS]
    c1 = [(sx*hw(z1), sy*hw(z1), z1) for sx,sy in SIGNS]
    add(f'DIA{pi:02d}a','横隔材', c1[0], c1[2], R_BR, '横隔')
    add(f'DIA{pi:02d}b','横隔材', c1[1], c1[3], R_BR, '横隔')
    for f in range(4):
        a0,b0 = c0[f], c0[(f+1)%4]
        a1,b1 = c1[f], c1[(f+1)%4]
        add(f'XB{pi:02d}f{f}a','塔身交叉斜材', a0, b1, R_BR, '塔身斜材')
        add(f'XB{pi:02d}f{f}b','塔身交叉斜材', b0, a1, R_BR, '塔身斜材')

# crossarms from 001 front view (bands), y=0 plane -> duplicate to ±325
for m in ca['members']:
    for syn, dy in ((1, -325.0), (-1, 325.0)):
        add('CA_'+m['mid'], m['role'],
            (m['p1'][0], dy, m['p1'][2]), (m['p2'][0], dy, m['p2'][2]), m['r_mm'], m['role'])

print(f'members: {len(members)}')
json.dump({'members': members, 'panel_z': panel_z,
           'hw_fn': 'fitted'}, open('demo/frame.json','w',encoding='utf-8'), ensure_ascii=False)

# SCAD
def scad_vec(p): return f"[{p[0]:.0f}, {p[1]:.0f}, {p[2]:.0f}]"
def color_of(mid):
    if mid.startswith('LEG'): return 'ForestGreen'
    if mid.startswith('DIA'): return 'SteelBlue'
    if mid.startswith('XB'): return 'DarkOrange'
    return 'Crimson'
out = ['// SZK31102A 135m 双回路直线塔 — 框架v2 (001正视图腿线拟合+横担带提取)',
       '// 1:1 mm; Z向上; 根开37560(135m呼高), 总高135000',
       '// 腿线=001正视图拟合(连续锥形+变坡); 横担=001正视图提取(前后片±325)',
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
