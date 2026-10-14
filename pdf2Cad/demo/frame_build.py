# -*- coding: utf-8 -*-
"""Tower frame v2: profile-following legs, panels, connected crossarms."""
import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('demo/data001.json', encoding='utf-8'))
RX0, RY0, RX1, RY1 = 60, 90, 1010, 3740
CX = 624.0
SCALE = 135000.0 / 3632.0
Y_BOT = 3749.0
def h(pt_y): return (Y_BOT - pt_y) * SCALE

# ---------- detect horizontal half-lines/lines ----------
Hs = []
for ln in data['lines']:
    (x0, y0), (x1, y1) = ln['a'], ln['b']
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    if not (RX0 <= mx <= RX1 and RY0 <= my <= RY1):
        continue
    if abs(y0 - y1) > 1.0 or abs(x1 - x0) < 60:
        continue
    centered = (abs((x0 + x1) / 2 - CX) < 8 or abs(x0 - CX) < 8 or abs(x1 - CX) < 8)
    if not centered:
        continue
    span = max(abs(x1 - CX), abs(x0 - CX))
    Hs.append({'y': y0, 'span': span * SCALE})

Hs.sort(key=lambda s: -s['y'])
levels = []
for s in Hs:
    if levels and abs(levels[-1]['y'] - s['y']) < 12:
        levels[-1]['span'] = max(levels[-1]['span'], s['span'])
        continue
    levels.append(dict(s))

HW_BASE = 37560 / 2.0
Z_TOT = 135000.0
# body taper reference (straight base->top) for crossarm outlier test
def taper_ref(z):
    return HW_BASE + (1600.0 - HW_BASE) * z / Z_TOT

# profile points: monotonic non-increasing half-width with height
prof = []
for lv in levels:
    z, w = h(lv['y']), lv['span']
    if z < 8000:                   # base/塔脚大样 lines: skip
        continue
    if prof:
        zt, wt = prof[-1]
        if z - zt < 500:           # merge close levels (keep wider)
            if w > wt: prof[-1] = (z, w)
            continue
        if w > wt:                 # violates monotonic taper -> crossarm/root line
            continue
    prof.append((z, w))
# force base & top
if prof[0][0] > 100: prof.insert(0, (0.0, HW_BASE))
if prof[-1][0] < Z_TOT - 100: prof.append((Z_TOT, 1600.0))
print('profile:')
for z, w in prof:
    print(f'  z={z:8.0f}  hw={w:8.0f}')

def hw_at(z):
    for i in range(len(prof) - 1):
        z0, w0 = prof[i]; z1, w1 = prof[i + 1]
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0) if z1 > z0 else 0
            return w0 + (w1 - w0) * t
    return prof[-1][1]

# ---------- crossarm levels: levels wider than taper reference ----------
cross_lvl = [(h(lv['y']), lv['span'], lv['y']) for lv in levels
             if lv['span'] > taper_ref(h(lv['y'])) * 1.5 and lv['span'] > 5000]
# cluster within 4000mm height, keep max reach
# 注: 最顶部的宽层(z≈134979)是地线顶架, 不是导线横担层 — 001共3层导线横担:
#   第一层(构件1,2,详图004) / 第二层(构件3,详图007+050) / 第三层(构件4,详图010)
cross_lvl.sort(key=lambda t: -t[0])
cas = []
for z, w, ypt in cross_lvl:
    if cas and abs(cas[-1][0] - z) < 4000:
        if w > cas[-1][1]: cas[-1] = [z, w]
        continue
    cas.append([z, w])
# 地线顶架 = 最高的一层, 从导线横担中剔除
if len(cas) >= 4:
    cas = cas[1:]
CA_META = ['第一层横担(构件1,2|详图004)', '第二层横担(构件3|详图007/050)',
           '第三层横担(构件4|详图010)']
cas = [dict(z=z, reach=w, meta=CA_META[i] if i < len(CA_META) else '')
       for i, (z, w) in enumerate(cas)]
print('crossarm levels:', [(round(c['z']), round(c['reach']), c['meta']) for c in cas])

# ---------- members ----------
members = []
def add(mid, spec, p1, p2, r, role):
    members.append({'mid': mid, 'spec': spec, 'role': role, 'r_mm': r,
                    'p1': [round(v, 1) for v in p1],
                    'p2': [round(v, 1) for v in p2]})

R_LEG, R_BR, R_CA = 180.0, 80.0, 130.0
LEG_SPEC = '主材(规格待部段图细化)'
CORNER_SIGNS = [(1, 1), (-1, 1), (-1, -1), (1, -1)]

# legs: polyline through profile, split per profile interval
for si, (sx, sy) in enumerate(CORNER_SIGNS):
    for i in range(len(prof) - 1):
        z0, w0 = prof[i]; z1, w1 = prof[i + 1]
        add(f'LEG{si}{i:02d}', LEG_SPEC,
            (sx * w0, sy * w0, z0), (sx * w1, sy * w1, z1), R_LEG, '塔身主材分段')

# panels between consecutive profile levels: diaphragms + X bracing per face
n_pan = len(prof) - 1
for pi in range(n_pan):
    z1, w1 = prof[pi]; z0, w0 = prof[pi + 1]
    c1 = [(sx * w1, sy * w1, z1) for sx, sy in CORNER_SIGNS]
    c0 = [(sx * w0, sy * w0, z0) for sx, sy in CORNER_SIGNS]
    add(f'DIA{pi:02d}a', '横隔材(待细化)', c1[0], c1[2], R_BR, '横隔')
    add(f'DIA{pi:02d}b', '横隔材(待细化)', c1[1], c1[3], R_BR, '横隔')
    for f in range(4):
        a1, b1 = c1[f], c1[(f + 1) % 4]
        a0, b0 = c0[f], c0[(f + 1) % 4]
        add(f'XB{pi:02d}f{f}a', '塔身交叉斜材(待细化)', a1, b0, R_BR, '塔身斜材')
        add(f'XB{pi:02d}f{f}b', '塔身交叉斜材(待细化)', b1, a0, R_BR, '塔身斜材')

# crossarms: Fink-profile cantilever truss per 004 —
#   plan: 双下弦 ±650 收尖 (2直角三角形), 顶弦投影重合(前后片, 前/后标注)
#   elevation: 顶弦 +4000下弯 -> +2200(②段) -> 上翘 +4000(①段挂点) -> 尖端
#   腹杆: W折线侧面斜材(~2100节间) + 平面斜材(147/148类) + 横隔框架(177/178类)
PROF_ROOT, PROF_KINK, PROF_PEAK = 4000.0, 2200.0, 4000.0
KINK_FRAC, PEAK_FRAC = 0.52, 0.80   # 沿悬臂位置比例(自004立面 9200/17500≈0.52, 峰值+6100)
ROOT_HW = 650.0
for ci, ca in enumerate(cas):
    z, reach = ca['z'], ca['reach']
    face_x = hw_at(z)                  # body face distance from centerline
    tip_x = reach                      # tip distance from centerline
    cant = tip_x - face_x              # cantilever length
    xk = face_x + cant * KINK_FRAC     # 顶弦折点
    xp = face_x + cant * PEAK_FRAC     # 挂点峰值
    panel_n = 5
    for sxn in (1, -1):                # both tower sides
        X = lambda v: sxn * v
        # 横隔框架 (根部/折点/峰值处, 前后片连接)
        for fi, fx in enumerate([face_x, xk, xp]):
            zz = z + (PROF_ROOT if fi == 0 else (PROF_KINK if fi == 1 else PROF_PEAK))
            w_i = ROOT_HW * (1 - (face_x and 0) - 0.15 * fi)
            add(f'CA{ci}s{sxn}TF{fi}', '横担横隔框架(177/178类)',
                (X(fx), -w_i, zz), (X(fx), w_i, zz), R_BR, '横担横隔')
        for syn in (1, -1):            # side planes (前/后片)
            Y = lambda v: syn * v
            y0 = Y(ROOT_HW)
            # 下弦 (2601/2602类): 根 -> 尖, 水平
            add(f'CA{ci}s{sxn}p{syn}BC', '横担下弦(2601/2602类)',
                (X(face_x), y0, z), (X(tip_x), 0.0, z), R_CA, '横担下弦')
            # 顶弦折线: 根+4000 -> 折点+2200 -> 峰+4000 -> 尖端+2200
            top_pts = [(X(face_x), y0, z + PROF_ROOT),
                       (X(xk), Y(ROOT_HW * 0.85), z + PROF_KINK),
                       (X(xp), 0.0, z + PROF_PEAK),
                       (X(tip_x), 0.0, z + PROF_KINK)]
            for k in range(3):
                nm = '横担顶弦②(1/2类)' if k == 0 else '横担顶弦①上翘段'
                add(f'CA{ci}s{sxn}p{syn}TC{k}', nm, top_pts[k], top_pts[k + 1], R_CA, '横担顶弦')
            # 根部立杆
            add(f'CA{ci}s{sxn}p{syn}RV', '横担根部立杆',
                (X(face_x), y0, z), (X(face_x), y0, z + PROF_ROOT), R_BR, '横担根部立杆')
            # W折线侧面斜材: 每节间一根, 交替方向 /\/\
            bot_nodes, top_nodes = [], []
            for k in range(panel_n + 1):
                t = k / panel_n
                bot_nodes.append((X(face_x + (tip_x - face_x) * t),
                                  Y(ROOT_HW * (1 - t)), z))
            for k in range(panel_n):
                tn = (k + 0.5) / panel_n
                tx = face_x + (tip_x - face_x) * tn
                ty = ROOT_HW * (1 - tn)
                if tn < KINK_FRAC:
                    tz = z + PROF_ROOT + (PROF_KINK - PROF_ROOT) * (tn / KINK_FRAC)
                elif tn < PEAK_FRAC:
                    tz = z + PROF_KINK + (PROF_PEAK - PROF_KINK) * ((tn - KINK_FRAC) / (PEAK_FRAC - KINK_FRAC))
                else:
                    tz = z + PROF_PEAK + (PROF_KINK - PROF_PEAK) * ((tn - PEAK_FRAC) / (1 - PEAK_FRAC))
                top_nodes.append((X(tx), Y(ty), tz))
            for k in range(panel_n):
                if k % 2 == 0:
                    a, b = bot_nodes[k], top_nodes[k]
                else:
                    a, b = bot_nodes[k + 1], top_nodes[k]
                add(f'CA{ci}s{sxn}p{syn}W{k}', '横担侧面斜材(W折线)',
                    a, b, R_BR, '横担侧面斜材')
            # 平面斜材 (147/148类): 前片下弦节点 -> 后片下弦节点
            if syn == 1:
                for k in range(1, panel_n, 2):
                    t = k / panel_n
                    bx = face_x + (tip_x - face_x) * t
                    by = ROOT_HW * (1 - t)
                    add(f'CA{ci}s{sxn}PD{k}', '横担平面斜材(147/148类)',
                        (X(bx), Y(by), z), (X(bx), -Y(by), z), R_BR, '横担平面斜材')
        # 挂点竖杆 (2607/135类): 峰值处的竖杆
        add(f'CA{ci}s{sxn}TP', '横担挂点竖杆(2607/135类)',
            (X(xp), 0.0, z), (X(xp), 0.0, z + PROF_PEAK), R_CA, '横担挂点竖杆')

print(f'members: {len(members)}')

json.dump({'scale': SCALE, 'members': members,
           'profile': prof, 'crossarms': cas},
          open('demo/frame.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('saved demo/frame.json')

# ---------- OpenSCAD ----------
def scad_vec(p):
    return f"[{p[0]:.0f}, {p[1]:.0f}, {p[2]:.0f}]"

def color_of(mid):
    if mid.startswith('LEG'): return 'ForestGreen'
    if mid.startswith('DIA'): return 'SteelBlue'
    if mid.startswith('XB'): return 'DarkOrange'
    return 'Crimson'

out = ['// SZK31102A 135m 双回路直线塔 — 全塔框架 (Stage A, 自001总图重建)',
       '// 1:1 mm; Z向上; 根开37560(135m呼高), 总高135000',
       '// Stage A=框架: 主材分段+横隔+交叉斜材+横担俯视三角架(前后片)',
       '// 横担层(z=114297)即050部段图对象: 下弦2601/2602 收尖相交',
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
    out.append(f"// {m['role']} {m['spec']}")
    out.append(f"tube({scad_vec(m['p1'])}, {scad_vec(m['p2'])}, {m['r_mm']:.0f}, \"{color_of(m['mid'])}\");")
    out.append('')
open('demo/tower_frame.scad', 'w', encoding='utf-8').write('\n'.join(out))
print('saved demo/tower_frame.scad')
