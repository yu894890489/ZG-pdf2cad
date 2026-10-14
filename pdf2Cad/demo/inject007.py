# -*- coding: utf-8 -*-
"""Inject real 007 crossarm into frame, replacing parametric level-2 (z=114297)."""
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

frame = json.load(open('demo/frame.json', encoding='utf-8'))
ca007 = json.load(open('demo/crossarm007.json', encoding='utf-8'))

CA_Z = 114297.0
X_CENTER_OFFSET = -11500.0   # real span 0..23000 centered on tower

# drop parametric level-2 crossarm members (CA1*)
kept, removed = [], 0
for m in frame['members']:
    if m['mid'].startswith('CA1'):
        removed += 1
        continue
    kept.append(m)
print(f'removed parametric level-2 members: {removed}')

for m in ca007['members']:
    p1 = [m['p1'][0] + X_CENTER_OFFSET, m['p1'][1], m['p1'][2] + CA_Z]
    p2 = [m['p2'][0] + X_CENTER_OFFSET, m['p2'][1], m['p2'][2] + CA_Z]
    kept.append({'mid': 'R07_' + m['mid'], 'spec': m['role'] + '(007图真实几何)',
                 'role': m['role'], 'r_mm': m['r_mm'],
                 'p1': [round(v, 1) for v in p1], 'p2': [round(v, 1) for v in p2]})

frame['members'] = kept
frame['crossarms_real'] = {'007': {'z': CA_Z, 'members': len(ca007['members']),
                                    'note': '第二层横担, 007图纸真实几何(立面W+俯视), 规格待表格分表解析后挂接'}}
json.dump(frame, open('demo/frame.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'frame members now: {len(kept)}')

# regenerate SCAD
def scad_vec(p):
    return f"[{p[0]:.0f}, {p[1]:.0f}, {p[2]:.0f}]"
def color_of(mid):
    if mid.startswith('LEG'): return 'ForestGreen'
    if mid.startswith('DIA'): return 'SteelBlue'
    if mid.startswith('XB'): return 'DarkOrange'
    if mid.startswith('R07'): return 'MediumOrchid'
    return 'Crimson'
out = ['// SZK31102A 135m 双回路直线塔 — 框架 + 007真实横担 (Stage B sample)',
       '// 1:1 mm; Z向上; 根开37560(135m呼高), 总高135000',
       '// 紫色 = 第二层横担(z=114297): 007图纸提取的真实几何杆件',
       '// 其余两层横担仍为参数化(004/010待同流水线提取)',
       '$fn = 32;', '',
       'module tube(p1, p2, r, col) {',
       '  v = p2 - p1;  L = norm(v);  ax = cross([0,0,1], v);',
       '  translate(p1) color(col)',
       '    if (norm(ax) < 1e-9)',
       '      rotate([0, v[2] > 0 ? 0 : 180, 0]) cylinder(h = L, r = r);',
       '    else',
       '      rotate(a = acos(min(1, max(-1, v[2]/L))), v = ax) cylinder(h = L, r = r);',
       '}', '']
for m in kept:
    out.append(f"// {m['role']} {m.get('spec','')}")
    out.append(f"tube({scad_vec(m['p1'])}, {scad_vec(m['p2'])}, {m['r_mm']:.0f}, \"{color_of(m['mid'])}\");")
    out.append('')
open('demo/tower_frame.scad', 'w', encoding='utf-8').write('\n'.join(out))
print('saved demo/tower_frame.scad')
