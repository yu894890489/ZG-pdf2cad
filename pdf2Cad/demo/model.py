# -*- coding: utf-8 -*-
"""Step 6 final: 3-stage model (naive -> cope -> plane-offset), collision check each stage."""
import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')

def isect(p1, p2, p3, p4):
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3; x4, y4 = p4
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-9: return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    return [x1 + t * (x2 - x1), y1 + t * (y2 - y1)]

AXIS_A = ([884.0, 1250.0], [1841.0, 263.0])
AXIS_B = ([1380.0, 768.0], [1849.0, 1231.0])
CL_2601, CL_2602, CL_2607, TOP_2607 = 1880.0, 1271.6, 1367.5, 545.0
A = [list(AXIS_A[0]), list(AXIS_A[1])]
B = [list(AXIS_B[0]), list(AXIS_B[1])]

NL = isect(A[0], A[1], [A[0][0], CL_2602], [A[1][0], CL_2602])
NT1 = isect(A[0], A[1], [CL_2601, 0], [CL_2601, 1700])
P = isect(A[0], A[1], B[0], B[1])
NR = isect(B[0], B[1], [CL_2601, 0], [CL_2601, 1700])

SCALE = 11847.0 / 1179.0
def mm(v): return v * SCALE

SPEC = {'2601': 'Q355φ356X7', '2602': 'Q355φ356X7', '2605': 'Q355φ299X6',
        '2607': 'Q355φ356X7', '2609': 'Q355φ273X5'}
TLEN = {'2601': 11847.0, '2602': 11847.0, '2605': 10185.0, '2607': 1927.0, '2609': 9234.0}

def r_of(spec):
    return float(spec.split('φ')[1].split('X')[0]) / 2.0

# mid, callout, axis, chord?, role
DEFS = [
    ('A',  '2605', [NL, NT1], False, '斜材 X(左下→右上), 前片'),
    ('B',  '2609', [P, NR],   False, '斜材 X(节点→右柱), 后片'),
    ('C1', '2607', [P, [CL_2607, TOP_2607]], True,  '横担弦杆(向上延续,跨图)'),
    ('C2', '2601', [NT1, NR], True,  '横担右弦柱'),
    ('H1', '2602', [[680.0, CL_2602], NR], True, '横担底部水平杆'),
]

def make(zoff):
    ms = []
    for mid, co, ax, chord, role in DEFS:
        spec = SPEC[co]
        r = r_of(spec)
        z = zoff.get(mid, 0.0)
        ms.append({'mid': mid, 'callout': co, 'chord': chord, 'role': role,
                   'spec': spec, 'r_mm': r, 'table_L': TLEN[co],
                   'p1': [round(mm(ax[0][0]), 1), round(-mm(ax[0][1]), 1), z],
                   'p2': [round(mm(ax[1][0]), 1), round(-mm(ax[1][1]), 1), z],
                   'a2d': ax[0], 'b2d': ax[1]})
    return ms

def seg_seg(p1, q1, p2, q2):
    d1 = [q1[i] - p1[i] for i in range(3)]
    d2 = [q2[i] - p2[i] for i in range(3)]
    r = [p1[i] - p2[i] for i in range(3)]
    a = sum(x * x for x in d1); e = sum(x * x for x in d2)
    f = sum(d2[i] * r[i] for i in range(3))
    c = sum(d1[i] * r[i] for i in range(3))
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
    return math.dist(cp1, cp2)

def collisions(ms):
    out = []
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            m1, m2 = ms[i], ms[j]
            d = seg_seg(m1['p1'], m1['p2'], m2['p1'], m2['p2'])
            pen = (m1['r_mm'] + m2['r_mm']) - d
            if pen > 1.0:
                out.append({'pair': [m1['mid'], m2['mid']],
                            'callouts': [m1['callout'], m2['callout']],
                            'pen': round(pen, 1)})
    return out

def cope_braces(ms):
    """trim brace ends at chord surfaces (dist to chord axis = R_chord), keep chord continuous"""
    for m in ms:
        if m['chord']: continue
        for c in ms:
            if not c['chord'] or c is m: continue
            for endi in (0, 1):
                p = m['p1'] if endi == 0 else m['p2']
                q = m['p2'] if endi == 0 else m['p1']
                # dist from p to chord infinite line
                e = [c['p2'][i] - c['p1'][i] for i in range(3)]
                L = math.sqrt(sum(x * x for x in e)); e = [x / L for x in e]
                w = [p[i] - c['p1'][i] for i in range(3)]
                tt = sum(w[i] * e[i] for i in range(3))
                cp = [c['p1'][i] + e[i] * tt for i in range(3)]
                dist = math.dist(p, cp)
                if dist >= c['r_mm']:
                    continue
                # move end back along axis to surface: dist(t) = R
                # p(t) = p + (q-p)*u ; solve |p(t)-cpline| = R
                v = [q[i] - p[i] for i in range(3)]
                Lv = math.sqrt(sum(x * x for x in v)); v = [x / Lv for x in v]
                # f(u) = |w + v*u*Lv - (cp + perp comp)|: dist to line = |(w + v*u*Lv) - proj|
                # proj of p onto line = cp ; dperp = p - cp
                dperp = [p[i] - cp[i] for i in range(3)]
                # |dperp + v*u*Lv| = R  ->  u^2*Lv^2 + 2u*Lv*(dperp·v) + |dperp|^2 - R^2 = 0
                bq = 2 * Lv * sum(dperp[i] * v[i] for i in range(3))
                cq = sum(x * x for x in dperp) - c['r_mm'] ** 2
                disc = bq * bq - 4 * Lv * Lv * cq
                if disc < 0: continue
                u = (-bq + math.sqrt(disc)) / (2 * Lv * Lv)
                if u < 0 or u > 1: continue
                newp = [p[i] + v[i] * Lv * u for i in range(3)]
                if endi == 0: m['p1'] = newp
                else: m['p2'] = newp
                m.setdefault('cope', []).append(c['callout'])

# ---- stage 1: naive z=0 ----
s1 = make({})
col1 = collisions(s1)
# ---- stage 2: cope braces, still z=0 ----
s2 = make({})
cope_braces(s2)
col2 = collisions(s2)
# ---- stage 3: plane offset from section view + cope ----
s3 = make({'A': -170.0, 'B': +170.0})
cope_braces(s3)
col3 = collisions(s3)

print(f'stage1 (初模 z=0):        {len(col1)} 处重合: {[(c["callouts"], c["pen"]) for c in col1]}')
print(f'stage2 (支管相贯修剪):    {len(col2)} 处重合: {[(c["callouts"], c["pen"]) for c in col2]}')
print(f'stage3 (前后片偏移+修剪): {len(col3)} 处重合')

for m in s3:
    L3 = math.dist(m['p1'], m['p2'])
    m['L_model_mm'] = round(L3, 0)
    print(f" {m['mid']} {m['callout']} {m['spec']} r={m['r_mm']:.0f} L={L3:.0f} (表长{m['table_L']:.0f}) cope={m.get('cope', [])}")

json.dump({'scale': SCALE, 'stages': {
    's1': {'members': s1, 'collisions': col1},
    's2': {'members': s2, 'collisions': col2},
    's3': {'members': s3, 'collisions': col3}}},
    open('demo/members.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('saved demo/members.json')
