# -*- coding: utf-8 -*-
"""Final model rebuild (6 evidenced members) + OpenSCAD export."""
import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')

def isect(p1, p2, p3, p4):
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3; x4, y4 = p4
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-9: return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    return [x1 + t * (x2 - x1), y1 + t * (y2 - y1)]

CL_2601 = 1271.6; CL_V = 1880.0; CL_2607 = 1367.5; TOP_2607 = 545.0
A = ([884.0, 1250.0], [1841.0, 263.0]); B = ([1380.0, 768.0], [1849.0, 1231.0])
NL = isect(A[0], A[1], [0, CL_2601], [3000, CL_2601])
NT1 = isect(A[0], A[1], [CL_V, 0], [CL_V, 1700])
P = isect(A[0], A[1], B[0], B[1])
NR = isect(B[0], B[1], [CL_V, 0], [CL_V, 1700])
SCALE = 11847.0 / 1179.0

def mm(v): return v * SCALE

SPEC = {'2601': 'Q355φ356X7', '2605': 'Q355φ299X6', '2606': 'Q355φ299X6',
        '2607': 'Q355φ356X7', '2608': 'Q355φ356X7', '2609': 'Q355φ273X5'}
TLEN = {'2601': 11847.0, '2605': 10185.0, '2606': 8785.0,
        '2607': 1927.0, '2608': 11400.0, '2609': 9234.0}

def r_of(s): return float(s.split('φ')[1].split('X')[0]) / 2.0

ZF, ZB = 650.0, -650.0
# 仅保留视图中有直接证据的杆件（去掉推定的后片底弦 2602）
DEFS = [
    ('D1', '2606', [NL, P], False, ZF, '斜材X·左臂(前片)'),
    ('D2', '2605', [NL, NT1], False, ZB, '斜材X·长臂(后片)'),
    ('D3', '2609', [P, NR], False, ZF, '斜材X·右臂(前片)'),
    ('C1', '2607', [P, [CL_2607, TOP_2607]], True, ZF, '横担前弦杆(向上延续)'),
    ('C2', '2608', [NT1, NR], True, ZB, '横担后弦柱(右端)'),
    ('H1', '2601', [[680.0, CL_2601], NR], True, ZF, '底部弦杆 L=11847'),
]

def make():
    ms = []
    for mid, co, ax, chord, z, role in DEFS:
        spec = SPEC[co]
        ms.append({'mid': mid, 'callout': co, 'chord': chord, 'role': role,
                   'spec': spec, 'r_mm': r_of(spec), 'table_L': TLEN[co],
                   'p1': [round(mm(ax[0][0]), 1), round(-mm(ax[0][1]), 1), z],
                   'p2': [round(mm(ax[1][0]), 1), round(-mm(ax[1][1]), 1), z]})
    return ms

def seg_seg(p1, q1, p2, q2):
    d1 = [q1[i] - p1[i] for i in range(3)]
    d2 = [q2[i] - p2[i] for i in range(3)]
    r = [p1[i] - p2[i] for i in range(3)]
    a = sum(x * x for x in d1); e = sum(x * x for x in d2)
    f = sum(d2[i] * r[i] for i in range(3)); c = sum(d1[i] * r[i] for i in range(3))
    b = sum(d1[i] * d2[i] for i in range(3))
    den = a * e - b * b
    s = 0.0
    if abs(den) > 1e-9:
        s = min(1.0, max(0.0, (b * f - c * e) / den))
    t = (b * s + f) / e
    if t < 0: t = 0.0; s = min(1.0, max(0.0, -c / a))
    elif t > 1: t = 1.0; s = min(1.0, max(0.0, (b - c) / a))
    cp1 = [p1[i] + d1[i] * s for i in range(3)]
    cp2 = [p2[i] + d2[i] * t for i in range(3)]
    return math.dist(cp1, cp2), s, t

def cope_braces(ms):
    for m in ms:
        if m['chord']: continue
        for c in ms:
            if not c['chord'] or c is m: continue
            e = [c['p2'][i] - c['p1'][i] for i in range(3)]
            Le = math.sqrt(sum(x * x for x in e)); e = [x / Le for x in e]
            for endi in (0, 1):
                p = m['p1'] if endi == 0 else m['p2']
                q = m['p2'] if endi == 0 else m['p1']
                w = [p[i] - c['p1'][i] for i in range(3)]
                tt = sum(w[i] * e[i] for i in range(3))
                cp = [c['p1'][i] + e[i] * tt for i in range(3)]
                dperp = [p[i] - cp[i] for i in range(3)]
                if math.sqrt(sum(x * x for x in dperp)) >= c['r_mm']:
                    continue
                v = [q[i] - p[i] for i in range(3)]
                Lv = math.sqrt(sum(x * x for x in v)); v = [x / Lv for x in v]
                step = [v[i] * Lv for i in range(3)]
                par = sum(step[i] * e[i] for i in range(3))
                wperp = [step[i] - par * e[i] for i in range(3)]
                a2 = sum(x * x for x in wperp)
                if a2 < 1e-9: continue
                b2 = 2 * sum(dperp[i] * wperp[i] for i in range(3))
                c2 = sum(x * x for x in dperp) - c['r_mm'] ** 2
                disc = b2 * b2 - 4 * a2 * c2
                if disc < 0: continue
                u = (-b2 + math.sqrt(disc)) / (2 * a2)
                if u < 0 or u > 1: continue
                newp = [p[i] + step[i] * u for i in range(3)]
                if endi == 0: m['p1'] = newp
                else: m['p2'] = newp
                m.setdefault('cope', []).append(c['callout'])

def check(ms, stage):
    out = []
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            m1, m2 = ms[i], ms[j]
            d, s, t = seg_seg(m1['p1'], m1['p2'], m2['p1'], m2['p2'])
            item = None
            bc = (not m1['chord'] and m2['chord']) or (m1['chord'] and not m2['chord'])
            if stage >= 2 and bc:
                br, ch = (m1, m2) if not m1['chord'] else (m2, m1)
                if stage >= 3 and ch['callout'] in br.get('cope', []):
                    pen = ch['r_mm'] - d
                    if pen > 0.5:
                        item = {'type': '干涉', 'why': '支管轴线侵入主管', 'pen': round(pen, 1)}
                else:
                    pen = (m1['r_mm'] + m2['r_mm']) - d
                    if pen > 0.5:
                        item = {'type': '干涉', 'why': '支管未修剪,端部伸入主管', 'pen': round(pen, 1)}
            elif m1['chord'] and m2['chord']:
                endmeet = (s > 0.85 or s < 0.15) and (t > 0.85 or t < 0.15)
                if endmeet:
                    item = {'type': '接触', 'why': '端面法兰连接(2FD3535B7H),允许接触', 'pen': 0.0}
                else:
                    pen = (m1['r_mm'] + m2['r_mm']) - d
                    if pen > 0.5:
                        item = {'type': '干涉', 'why': '主管实体相交', 'pen': round(pen, 1)}
            else:
                if stage >= 2:
                    item = {'type': '校核', 'why': '同节点多杆汇交,需节点板分隔校核',
                            'pen': round(max(0.0, (m1['r_mm'] + m2['r_mm']) - d), 1)}
                else:
                    pen = (m1['r_mm'] + m2['r_mm']) - d
                    if pen > 0.5:
                        item = {'type': '干涉', 'why': '斜材实体相交', 'pen': round(pen, 1)}
            if item:
                item['pair'] = [m1['mid'], m2['mid']]
                item['callouts'] = [m1['callout'], m2['callout']]
                out.append(item)
    return out

s1 = make(); c1 = check(s1, 1)
s2 = make(); c2 = check(s2, 2)
s3 = make(); cope_braces(s3); c3 = check(s3, 3)
for name, cc in (('S1', c1), ('S2', c2), ('S3', c3)):
    ni = sum(1 for x in cc if x['type'] == '干涉')
    print(f"{name}: 干涉{ni} 接触{sum(1 for x in cc if x['type']=='接触')} 校核{sum(1 for x in cc if x['type']=='校核')}")
    for x in cc:
        print('   ', x['callouts'], x['type'], x['pen'], 'mm', x['why'])
for m in s3:
    m['L_model_mm'] = round(math.dist(m['p1'], m['p2']), 0)

json.dump({'scale': SCALE, 'stages': {
    's1': {'members': s1, 'items': c1},
    's2': {'members': s2, 'items': c2},
    's3': {'members': s3, 'items': c3}},
    'final': s3}, open('demo/members.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('saved demo/members.json')

# ================= OpenSCAD export =================
def scad_vec(p):  # model(x, y=height, z=depth) -> scad(x, y=-depth, z=height)
    return f"[{p[0]:.1f}, {-p[2]:.1f}, {p[1]:.1f}]"

COLORS = {'2601': 'SteelBlue', '2607': 'ForestGreen', '2608': 'ForestGreen',
          '2605': 'DarkOrange', '2606': 'DarkOrange', '2609': 'DarkOrange'}
out = ['// SZK31102A 铁塔 050 横担部段 X节点群 — 由 PDF 图纸自动重建 (demo)',
       '// 比例: 1:1 (mm), 由 表长11847mm <-> 矢量提取1179pt 标定',
       '// 坐标系: X=图面横向, Y=图面深度(前片为+), Z=高度(上为正)',
       '// 件号与明细表对应关系见各行注释; 杆端已按主管表面相贯修剪',
       '$fn = 48;', '',
       'module tube(p1, p2, r, col) {',
       '  v = p2 - p1;',
       '  L = norm(v);',
       '  ax = cross([0,0,1], v);',
       '  translate(p1) color(col)',
       '    if (norm(ax) < 1e-9)',
       '      rotate([0, v[2] > 0 ? 0 : 180, 0]) cylinder(h = L, r = r);',
       '    else',
       '      rotate(a = acos(min(1, max(-1, v[2]/L))), v = ax) cylinder(h = L, r = r);',
       '}', '']
for m in s3:
    cope = '相贯修剪于 ' + ','.join(m['cope']) if m.get('cope') else '无修剪'
    out.append(f"// 件号 {m['callout']}  {m['spec']}  表长 {m['table_L']:.0f}mm  "
               f"模型段长 {m['L_model_mm']:.0f}mm  {m['role']}  {cope}")
    out.append(f"tube({scad_vec(m['p1'])}, {scad_vec(m['p2'])}, "
               f"{m['r_mm']:.1f}, \"{COLORS.get(m['callout'], 'Gray')}\");")
    out.append('')
open('demo/tower_050.scad', 'w', encoding='utf-8').write('\n'.join(out))
print('saved demo/tower_050.scad')
