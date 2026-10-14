# -*- coding: utf-8 -*-
"""修复三处：恢复第一层 + 去梳齿 + 展宽校准"""
import json, sys, math, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

frame = json.load(open('demo/frame.json', encoding='utf-8'))
cross = json.load(open('demo/all_crossarms_3d.json', encoding='utf-8'))

# 确保所有成员都有 mid 字段
for i, m in enumerate(frame['members']):
    if 'mid' not in m: m['mid'] = m.get('role', f'UNK_{i}')[:15]
for label in ('L2_mid', 'L3_low'):
    for i, m in enumerate(cross.get(label, [])):
        if 'mid' not in m: m['mid'] = f'{label}_{i:03d}'

prof = frame.get('profile', [])
def hw_at(z):
    if not prof: return 1800.0
    for i in range(len(prof)-1):
        z0,w0 = prof[i]; z1,w1 = prof[i+1]
        if z0 <= z <= z1:
            t = (z-z0)/(z1-z0) if z1>z0 else 0
            return w0 + (w1-w0)*t
    return prof[-1][1] if prof else 1800.0

# ==== FIX 1: 恢复第一层参数化 ====
CA0_Z = 129571.0
hw0 = hw_at(CA0_Z)
CA0_REACH = 5700.0
CA0_D_ROOT = 3300.0
CA0_D_TIP = 1000.0
CA0_SEP = 650.0
ca0 = []
n = 0
for sxn in (1, -1):
    X = lambda v: sxn * v
    face_x = hw0
    tip_x = CA0_REACH
    for syn in (1, -1):
        Y = lambda v: syn * v
        n += 1; ca0.append({'mid': f'PCA0_{n:03d}', 'role': 'L1下弦', 'r_mm': 90.0, 'spec': '参数化',
            'p1': [X(face_x), Y(CA0_SEP), CA0_Z], 'p2': [X(tip_x), 0.0, CA0_Z]})
        n += 1; ca0.append({'mid': f'PCA0_{n:03d}', 'role': 'L1上弦', 'r_mm': 90.0, 'spec': '参数化',
            'p1': [X(face_x), Y(CA0_SEP), CA0_Z+CA0_D_ROOT], 'p2': [X(tip_x), 0.0, CA0_Z+CA0_D_TIP]})
        n += 1; ca0.append({'mid': f'PCA0_{n:03d}', 'role': 'L1根部立杆', 'r_mm': 70.0, 'spec': '参数化',
            'p1': [X(face_x), Y(CA0_SEP), CA0_Z], 'p2': [X(face_x), Y(CA0_SEP), CA0_Z+CA0_D_ROOT]})
        n += 1; ca0.append({'mid': f'PCA0_{n:03d}', 'role': 'L1斜杆', 'r_mm': 55.0, 'spec': '参数化',
            'p1': [X(face_x), Y(CA0_SEP), CA0_Z+CA0_D_ROOT],
            'p2': [X(tip_x*0.5), Y(CA0_SEP/2), CA0_Z+(CA0_D_ROOT+CA0_D_TIP)/2]})
    n += 1; ca0.append({'mid': f'PCA0_{n:03d}', 'role': 'L1根横梁', 'r_mm': 90.0, 'spec': '参数化',
        'p1': [X(face_x), -CA0_SEP, CA0_Z], 'p2': [X(face_x), CA0_SEP, CA0_Z]})
    n += 1; ca0.append({'mid': f'PCA0_{n:03d}', 'role': 'L1挂点竖杆', 'r_mm': 70.0, 'spec': '参数化',
        'p1': [X(tip_x), 0.0, CA0_Z], 'p2': [X(tip_x), 0.0, CA0_Z+CA0_D_TIP]})
print(f'FIX1: L1 parametric {len(ca0)} members at z={CA0_Z}')

# ==== FIX 2: 去梳齿 ====
def filter_diaphragms(members, min_gap=2000.0):
    dias = sorted(set(m['p1'][0] for m in members if '横隔' in m['role']))
    kept_xs = []
    for x in dias:
        if not kept_xs or x - kept_xs[-1] > min_gap: kept_xs.append(x)
    result = []
    removed = 0
    for m in members:
        if '横隔' in m['role']:
            if any(abs(m['p1'][0]-x) < 100 for x in kept_xs):
                result.append(m)
            else: removed += 1
        else: result.append(m)
    return result, removed

L2 = cross.get('L2_mid', [])
L3 = cross.get('L3_low', [])
L2, rm2 = filter_diaphragms(L2)
L3, rm3 = filter_diaphragms(L3)
print(f'FIX2: L2 diaphragm {len(L2)+rm2} -> {len(L2)} (-{rm2})  L3 {len(L3)+rm3} -> {len(L3)} (-{rm3})')

# ==== FIX 3: 展宽校准 ====
# 001 reach: L2=11401mm, L3=12370mm (从中心线)
# DXF axis 包含根部段 → face_to_tip = axis_len
# 当前 tip_x = X_OFF + axis_len = 2238 + 19215 = 21453 (L2)
# 目标 tip = 11401 → scale = 11401 / 2238+19215 = 11401/21453 = 0.531
L2_tip_now = 2238 + 19215
L2_scale = 11401.0 / L2_tip_now
L3_tip_now = 2238 + 10476
L3_scale = 99152 - 99152 + 12370.0  # target reach for L3
L3_scale = 12370.0 / (2238 + 10476)
print(f'FIX3: L2 scale={L2_scale:.3f} L3 scale={L3_scale:.3f}')

def rescale_x(ms, s):
    for m in ms:
        m['p1'][0] = round(m['p1'][0]*s, 1)
        m['p2'][0] = round(m['p2'][0]*s, 1)
    return ms
L2 = rescale_x(L2, L2_scale)
L3 = rescale_x(L3, L3_scale)

# ==== 拼装 ====
base = [m for m in frame['members'] if not m.get('mid','').startswith('CA') and not m.get('mid','').startswith('L2') and not m.get('mid','').startswith('L3')]
all_m = base + ca0 + L2 + L3
print(f'total: {len(all_m)} (base {len(base)} + L1 {len(ca0)} + L2 {len(L2)} + L3 {len(L3)})')
frame['members'] = all_m
json.dump(frame, open('demo/frame.json', 'w', encoding='utf-8'), ensure_ascii=False)

# SCAD
def sv(p): return f"[{p[0]:.0f}, {p[1]:.0f}, {p[2]:.0f}]"
def col(mid=""):
    if mid.startswith('LEG'): return 'ForestGreen'
    if mid.startswith('BR'): return 'DarkOrange'
    if 'L1' in mid or mid.startswith('PCA0'): return 'Crimson'
    if mid.startswith('L2'): return 'Crimson'
    if mid.startswith('L3'): return 'MediumOrchid'
    return 'SteelBlue'
out = ['// SZK31102A 135m — 全塔v2 (FIX1 第一层恢复 + FIX2 去梳齿 + FIX3 展宽校准)',
       '// 1:1mm; 根开37560; 总高135000', '$fn=32;', '',
       'module tube(p1,p2,r,col){v=p2-p1;L=norm(v);ax=cross([0,0,1],v);translate(p1)color(col)if(norm(ax)<1e-9)rotate([0,v[2]>0?0:180,0])cylinder(h=L,r=r);else rotate(a=acos(min(1,max(-1,v[2]/L))),v=ax)cylinder(h=L,r=r);}', '']
for m in all_m:
    out.append(f'tube({sv(m["p1"])},{sv(m["p2"])},{m["r_mm"]:.0f},"{col(m["mid"])}");')
open('demo/tower_frame.scad', 'w', encoding='utf-8').write('\n'.join(out))
print('scad saved')

# 渲染正视图对比
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import ezdxf
d1 = json.load(open('demo/data001.json', encoding='utf-8'))
CX, Y_BOT, SC001 = 624.0, 3749.0, 135000.0/3632.0
fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 14), sharey=True)
for ln in d1['lines']:
    (xa, ya), (xb, yb) = ln['a'], ln['b']
    mx = (xa+xb)/2
    if not (100 <= mx <= 1150): continue
    a1.plot([(xa-CX)*SC001, (xb-CX)*SC001], [(Y_BOT-ya)*SC001, (Y_BOT-yb)*SC001], color='black', lw=0.4)
a1.set_title('001 drawing'); a1.set_xlim(-22000, 22000); a1.set_ylim(-3000, 140000); a1.set_aspect('equal')
for m in all_m:
    p1, p2 = m['p1'], m['p2']
    mid = m.get('mid','')
    c = 'gray'
    if mid.startswith('LEG'): c = 'green'
    elif mid.startswith('XB'): c = 'darkorange'
    elif mid.startswith('DIA'): c = 'steelblue'
    elif 'L1' in mid or mid.startswith('PCA0'): c = 'crimson'
    elif mid.startswith('L2'): c = 'crimson'
    elif mid.startswith('L3'): c = 'mediumorchid'
    a2.plot([p1[0],p2[0]],[p1[2],p2[2]], color=c, lw=0.5)
a2.set_title('fixed model'); a2.set_xlim(-22000, 22000); a2.set_ylim(-3000, 140000); a2.set_aspect('equal')
plt.tight_layout(); plt.savefig('demo/compare_v2_fix.png', dpi=85)
print('saved compare_v2_fix.png')
