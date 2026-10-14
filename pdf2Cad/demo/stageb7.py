# -*- coding: utf-8 -*-
"""Generalized crossarm assembler: plan extraction -> node graph -> 3D -> inject.
Usage: python stageb7.py <sheet> <CA_Z> <singleline_region x0,y0,x1,y1> <plan_region x0,y0,x1,y1>"""
import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')

SHEET = sys.argv[1]
CA_Z = float(sys.argv[2])
SGL = tuple(float(v) for v in sys.argv[3].split(','))
REG = tuple(float(v) for v in sys.argv[4].split(','))
print(f'=== sheet {SHEET} CA_Z={CA_Z} ===')

d = json.load(open(f'demo/stageb_{SHEET}.json', encoding='utf-8'))
d2 = json.load(open(f'demo/stageb2_{SHEET}.json', encoding='utf-8'))
clusters, circles = d2['clusters'], d2['plan_circles']

def in_reg(c, reg):
    return all(reg[0] <= p[0] <= reg[2] and reg[1] <= p[1] <= reg[3] for p in (c['a'], c['b']))

# ---------- 1. chords: longest cluster + first non-colinear long cluster, midline their colinear families ----------
def unit(c):
    dx, dy = c['b'][0]-c['a'][0], c['b'][1]-c['a'][1]
    L = math.hypot(dx, dy)
    return dx/L, dy/L, L

main = [c for c in clusters if in_reg(c, REG) and c['ext'] > 50]
by_ext = sorted(main, key=lambda c: -c['ext'])
maxext = by_ext[0]['ext']

def perp_off(c1, c2):
    ux, uy, L = unit(c1)
    o = -(c2['a'][0]-c1['a'][0])*uy + (c2['a'][1]-c1['a'][1])*ux
    return abs(o)

chord1_raw = by_ext[0]
chord2_raw = next(c for c in by_ext[1:]
                  if c['ext'] > maxext * 0.8 and perp_off(chord1_raw, c) > 100)

def midline(fam):
    ref = max(fam, key=lambda c: c['ext'])
    out_a, out_b = [ref['a']], [ref['b']]
    for c in fam:
        if c is ref: continue
        if math.dist(c['a'], ref['a']) + math.dist(c['b'], ref['b']) <=            math.dist(c['b'], ref['a']) + math.dist(c['a'], ref['b']):
            out_a.append(c['a']); out_b.append(c['b'])
        else:
            out_a.append(c['b']); out_b.append(c['a'])
    return {'a': [sum(v)/len(v) for v in zip(*out_a)],
            'b': [sum(v)/len(v) for v in zip(*out_b)], 'ext': ref['ext'], 'ang': ref['ang']}

fam1 = [c for c in main if c['ext'] > maxext*0.4 and perp_off(chord1_raw, c) < 25]
fam2 = [c for c in main if c['ext'] > maxext*0.4 and perp_off(chord2_raw, c) < 25]
chords = [midline(fam1), midline(fam2)]
for c in chords:
    print(f"  chord ({c['a'][0]:.0f},{c['a'][1]:.0f})-({c['b'][0]:.0f},{c['b'][1]:.0f}) fam={len(fam1)},{len(fam2)}")

# ---------- 2. node graph ----------
nodes = []
def snap(p, tol=28.0):
    for i, q in enumerate(nodes):
        if math.dist(p, q) < tol: return i
    nodes.append(list(p)); return len(nodes) - 1

members = []
def add_mem(p1, p2, role, r):
    i1, i2 = snap(p1), snap(p2)
    if i1 == i2: return
    members.append({'n1': i1, 'n2': i2, 'role': role, 'r_mm': r})

def orient(c):
    a, b = c['a'], c['b']
    return (a, b) if a[0] <= b[0] else (b, a)

ca_, cb_ = orient(chords[0])
c2a, c2b = orient(chords[1])
u1 = ((cb_[0]-ca_[0])/chords[0]['ext'], (cb_[1]-ca_[1])/chords[0]['ext'])

brac = [c for c in main if c not in fam1 and c not in fam2 and c['ext'] > 60]
print(f'bracing axes: {len(brac)}')

def proj(c, p):
    ux, uy, L = unit(c)
    return (p[0]-c['a'][0])*ux + (p[1]-c['a'][1])*uy
def point_on(c, t):
    ux, uy, L = unit(c)
    return [c['a'][0]+ux*t, c['a'][1]+uy*t]

stations = set()
for c in brac:
    for p in (c['a'], c['b']):
        for cc, LL in ((chords[0], chords[0]['ext']), (chords[1], chords[1]['ext'])):
            t = proj(cc, p)
            if -40 <= t <= LL + 40: stations.add(round(t/20)*20)
stations = sorted(stations)
merged = []
for s in stations:
    if merged and s - merged[-1] < 60: continue
    merged.append(s)
for ci, c in enumerate(chords):
    prev = None
    for s in merged:
        if s > c['ext']: break
        if prev is not None:
            add_mem(point_on(c, prev), point_on(c, s), f'弦杆{ci+1}', 105.0)
        prev = s
for c in brac:
    add_mem(c['a'], c['b'], 'X平面斜材' if c['ext'] > 250 else '连接件', 40.0)
print(f'nodes: {len(nodes)}, plan members: {len(members)}')

# ---------- 3. 3D: 视图=下平面(前后片下弦真实平面位置), 高度=单线图轮廓, 上弦参数化补齐 ----------
SC = 10.6
bc, tc = chords[1], chords[0]
def perp_dist(c, p):
    ux, uy, L = unit(c)
    return -(p[0]-c['a'][0])*uy + (p[1]-c['a'][1])*ux
# 轴线 = 两弦中线; 根部 = 窄端 (塔身面), 尖端 = 宽端 (挂点)
axA = [(chords[0]['a'][0]+chords[1]['a'][0])/2, (chords[0]['a'][1]+chords[1]['a'][1])/2]
axB = [(chords[0]['b'][0]+chords[1]['b'][0])/2, (chords[0]['b'][1]+chords[1]['b'][1])/2]
dA = math.dist(chords[0]['a'], chords[1]['a'])
dB = math.dist(chords[0]['b'], chords[1]['b'])
if dA > dB:
    axA, axB = axB, axA
dd = math.dist(axA, axB) or 1
aux, auy = (axB[0]-axA[0])/dd, (axB[1]-axA[1])/dd
AXL = dd
SEP_ROOT = min(dA, dB) * SC
SEP_TIP = max(dA, dB) * SC
print(f'axis len={AXL*SC:.0f}mm, plan spread root={SEP_ROOT:.0f} -> tip={SEP_TIP:.0f}')

# z 轮廓: 桁架高度(上弦在下弦之上) — 单线图两线间距, 按图纸第一层深度尺度收正
sg = []
for ln in d['lines']:
    (x0, y0), (x1, y1) = ln['a'], ln['b']
    mx, my = (x0+x1)/2, (y0+y1)/2
    if SGL[0] <= mx <= SGL[2] and SGL[1] <= my <= SGL[3] and math.dist(ln['a'], ln['b']) > 60:
        sg.append(ln)
seps = []
if len(sg) >= 2:
    for i in range(len(sg)):
        for j in range(i+1, len(sg)):
            for pa in (sg[i]['a'], sg[i]['b']):
                for pb in (sg[j]['a'], sg[j]['b']):
                    if abs(pa[0]-pb[0]) < 30:
                        seps.append(abs(pa[1]-pb[1]))
raw_root = max(seps) if seps else 160.0
raw_tip = min(seps) if seps else 30.0
S150 = 0.3528 * 150
D_ROOT = min(raw_root * S150, 4600.0)   # 001正视图标定: 根部桁架高≈4.6m
D_TIP = max(min(raw_tip * S150, D_ROOT * 0.6), 800.0)
print(f'depth profile: root={D_ROOT:.0f} -> tip={D_TIP:.0f}')

def node_3d(p):
    t = (p[0]-axA[0])*aux + (p[1]-axA[1])*aux and 0 or ((p[0]-axA[0])*aux + (p[1]-axA[1])*auy)
    xn = max(0.0, min(1.0, t/AXL))
    oy = -(p[0]-axA[0])*auy + (p[1]-axA[1])*aux
    # 平面展宽: 视图垂距 -> 真实y (保留符号, 按端部间距归一)
    half_root, half_tip = SEP_ROOT/2, SEP_TIP/2
    sign = 1 if oy >= 0 else -1
    frac = abs(oy) / (max(dA, dB)/2)
    y = sign * (half_root + (half_tip - half_root) * xn) * min(1.0, frac / max(1e-6, abs(oy)/ (max(dA,dB)/2 + 1e-9)) )
    y = sign * abs(oy) * SC * ( (half_root + (half_tip-half_root)*xn) / (max(dA,dB)/2) )
    z = 0.0
    return [round(t*SC,1), round(y,1), round(z,1)]

members3d = []
for m in members:
    p1, p2 = nodes[m['n1']], nodes[m['n2']]
    w1, w2 = node_3d(p1), node_3d(p2)
    if math.dist(w1, w2) < 80: continue
    members3d.append({'role': m['role'], 'r_mm': m['r_mm'], 'p1': w1, 'p2': w2})
# 参数化上弦三角 (每侧片): 根部高D_ROOT -> 尖端D_TIP, 沿各自弦平面
tip_x = AXL * SC
for sgn in (1, -1):
    y_root = sgn * SEP_ROOT / 2
    y_tip = sgn * SEP_TIP / 2
    members3d.append({'role': '上弦(参数化)', 'r_mm': 90.0,
        'p1': [0.0, round(y_root,1), round(D_ROOT,1)],
        'p2': [round(tip_x,1), round(y_tip,1), round(D_TIP,1)]})
    members3d.append({'role': '根部立杆(参数化)', 'r_mm': 70.0,
        'p1': [0.0, round(y_root,1), 0.0],
        'p2': [0.0, round(y_root,1), round(D_ROOT,1)]})
    members3d.append({'role': '上弦斜杆(参数化)', 'r_mm': 55.0,
        'p1': [0.0, round(y_root,1), round(D_ROOT,1)],
        'p2': [round(tip_x*0.5,1), round((y_root+y_tip)/2,1), 0.0]})
xs = [p['p1'][0] for p in members3d] + [p['p2'][0] for p in members3d]
print(f'3D members: {len(members3d)}, x span {min(xs):.0f}..{max(xs):.0f}')
json.dump({'members': members3d, 'scale': SC, 'ca_z': CA_Z},
          open(f'demo/crossarm{SHEET}_v1.json', 'w', encoding='utf-8'), ensure_ascii=False)

# ---------- 4. inject: replace parametric CA level + mirror + connect ----------
frame = json.load(open('demo/frame.json', encoding='utf-8'))
prof = frame['profile']
def hw_at(z):
    for i in range(len(prof)-1):
        z0, w0 = prof[i]; z1, w1 = prof[i+1]
        if z0 <= z <= z1:
            t = (z-z0)/(z1-z0) if z1 > z0 else 0
            return w0 + (w1-w0)*t
    return prof[-1][1]
hw_b = hw_at(CA_Z)
hw_t = hw_at(CA_Z + D_ROOT)
X_OFF = hw_b
# which CA level does this sheet replace? find parametric CA level within 3000mm
ca_idx = None
for ci in range(10):
    has = any(m['mid'].startswith(f'CA{ci}') for m in frame['members'])
    if has:
        zl = [m['p1'][2] for m in frame['members'] if m['mid'].startswith(f'CA{ci}')][0]
        if abs(zl - CA_Z) < 5500:
            ca_idx = ci; break
label = f'CA{ca_idx}' if ca_idx is not None else 'CA?'
before = len(frame['members'])
frame['members'] = [m for m in frame['members'] if not m['mid'].startswith(label)]
print(f'replaced parametric {label}: {before} -> {len(frame["members"])}')

for i, m in enumerate(members3d):
    rr = 40.0 if '斜材' in m['role'] or '连接' in m['role'] else m['r_mm']
    frame['members'].append({'mid': f'R{SHEET}_{i:03d}', 'spec': m['role'] + f'({SHEET}真实几何)',
                             'role': m['role'], 'r_mm': rr,
                             'p1': [round(m['p1'][0]+X_OFF,1), m['p1'][1], round(m['p1'][2]+CA_Z,1)],
                             'p2': [round(m['p2'][0]+X_OFF,1), m['p2'][1], round(m['p2'][2]+CA_Z,1)]})
# mirror to -X
base = [m for m in frame['members'] if m['mid'].startswith(f'R{SHEET}_')]
for m in base:
    m2 = dict(m); m2['mid'] = 'M' + m['mid']
    m2['p1'] = [-m['p1'][0], m['p1'][1], m['p1'][2]]
    m2['p2'] = [-m['p2'][0], m['p2'][1], m['p2'][2]]
    m2['spec'] = m['spec'] + '(镜像)'
    frame['members'].append(m2)
# root connections (推定): 根节点(窄端) -> 塔身角点/面
sep_r = SEP_ROOT / 2
ZT = CA_Z + D_ROOT
hw_t2 = hw_at(CA_Z + D_ROOT)
def add_rt(p1, p2, role, r=90.0):
    frame['members'].append({'mid': f'RT{SHEET}_{len(frame["members"]):03d}',
        'spec': '根部连接(推定)', 'role': role, 'r_mm': r,
        'p1': [round(v,1) for v in p1], 'p2': [round(v,1) for v in p2]})
for syn in (1, -1):
    ry = syn * sep_r
    add_rt((X_OFF, ry, CA_Z), (hw_b, syn*hw_b, CA_Z), '下弦根->角点')
    add_rt((X_OFF, ry, D_ROOT), (hw_t2, syn*hw_t2, CA_Z + D_ROOT), '上弦根->上层角点')
    add_rt((X_OFF, ry, CA_Z), (X_OFF, ry, D_ROOT), '根部立杆')
add_rt((X_OFF, -sep_r, CA_Z), (X_OFF, sep_r, CA_Z), '根部横梁')
json.dump(frame, open('demo/frame.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'frame total: {len(frame["members"])}')
