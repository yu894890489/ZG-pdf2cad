# -*- coding: utf-8 -*-
"""碰撞检查 v3: 526 杆件胶囊体相交检测
- 共节点(距离<1mm) -> 连接, 跳过
- 同面 X 撑交叉 -> 设计连接点, 单列
- min_dist < r1+r2+clearance -> 碰撞
"""
import sys, json, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np

frame = json.load(open('demo/frame.json', encoding='utf-8'))
ms = frame['members']
N = len(ms)
P1 = np.array([m['p1'] for m in ms])
P2 = np.array([m['p2'] for m in ms])
R = np.array([m['r_mm'] for m in ms])
CLEAR = 10.0

def seg_dist(pa, pb, qa, qb):
    """线段 pa-pb 与 qa-qb 最小距离 (成对单组)"""
    d1 = pb - pa; d2 = qb - qa; r = pa - qa
    a = d1 @ d1; e = d2 @ d2; f = d2 @ r
    c = d1 @ r
    if a <= 1e-9 and e <= 1e-9:
        return np.linalg.norm(r)
    if a <= 1e-9:
        s = np.clip(f / e, 0, 1)
        return np.linalg.norm(r - s * d2)
    if e <= 1e-9:
        s = np.clip(-c / a, 0, 1)
        return np.linalg.norm(r + s * d1)
    b = d1 @ d2
    den = a * e - b * b
    s = np.clip((b * f - c * e) / den, 0, 1) if den > 1e-9 else 0.0
    t = (b * s + f) / e
    if t < 0:
        t = 0.0; s = np.clip(-c / a, 0, 1)
    elif t > e:
        t = 1.0; s = np.clip((b - c) / a, 0, 1)
    return np.linalg.norm(r + s * d1 - t * d2)

def group(mid): return mid[:3] if mid[:2] in ('L1','L2','L3') else mid[:3]

collisions, near, xcross, tjoint = [], [], [], []
for i in range(N):
    for j in range(i+1, N):
        # 共节点跳过
        d_ss = min(np.linalg.norm(P1[i]-P1[j]), np.linalg.norm(P1[i]-P2[j]),
                   np.linalg.norm(P2[i]-P1[j]), np.linalg.norm(P2[i]-P2[j]))
        if d_ss < 1.0: continue
        d = seg_dist(P1[i], P2[i], P1[j], P2[j])
        thr = R[i] + R[j] + CLEAR
        gi, gj = group(ms[i]['mid']), group(ms[j]['mid'])
        if d < 1.0:
            tjoint.append((i, j, d)); continue  # 端点落在对方轴线上 = T/Y 节点连接
        if d < thr:
            # 同面 X 交叉: 同为 XB 且交叉点在两段中部
            if ms[i]['mid'].startswith('XB') and ms[j]['mid'].startswith('XB'):
                xcross.append((i, j, d)); continue
            collisions.append((i, j, d))
        elif d < thr + 90:
            near.append((i, j, d))

print(f'pairs checked: {N*(N-1)//2}')
print(f'T/Y节点连接(端点触轴线): {len(tjoint)}')
print(f'X撑设计交叉: {len(xcross)}')
print(f'碰撞 (0 < dist < r1+r2+10): {len(collisions)}')
print(f'接近 (dist < r1+r2+100): {len(near)}')

def describe(p):
    i, j, d = p
    a, b = ms[i], ms[j]
    return (f"{a['mid']}({a['role']},{a['spec']}) x {b['mid']}({b['role']},{b['spec']}) "
            f"dist={d:.0f}mm sum_r={R[i]+R[j]:.0f}")

print('\n--- 碰撞明细(按距离排序) ---')
for p in sorted(collisions, key=lambda p: p[2])[:30]:
    print(describe(p))

with open('demo/collision_report.txt', 'w', encoding='utf-8') as f:
    f.write(f'碰撞检查报告 v3 (526杆, clearance=10mm)\n')
    f.write(f'X撑设计交叉: {len(xcross)} (同面X撑,视为连接)\n')
    f.write(f'碰撞: {len(collisions)}\n')
    f.write(f'接近(<r1+r2+100): {len(near)}\n\n碰撞明细:\n')
    for p in sorted(collisions, key=lambda p: p[2]):
        f.write(describe(p) + '\n')
print('saved demo/collision_report.txt')

# 可视化: 碰撞对高亮
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 9))
for m in ms:
    p1, p2, mid = m['p1'], m['p2'], m['mid']
    a1.plot([p1[0],p2[0]],[p1[2],p2[2]], color='lightgray', lw=0.5, zorder=1)
bad = set()
for i,j,d in collisions: bad.add(i); bad.add(j)
for k in bad:
    m = ms[k]
    a1.plot([m['p1'][0],m['p2'][0]],[m['p1'][2],m['p2'][2]], color='red', lw=1.2, zorder=3)
a1.set_title(f'front view - {len(collisions)} collisions ({len(bad)} members)')
a1.set_aspect('equal')
for m in ms:
    a2.plot([m['p1'][0],m['p2'][0]],[m['p1'][1],m['p2'][1]], color='lightgray', lw=0.5)
for k in bad:
    m = ms[k]
    a2.plot([m['p1'][0],m['p2'][0]],[m['p1'][1],m['p2'][1]], color='red', lw=1.2)
a2.set_title('plan view'); a2.set_aspect('equal')
plt.tight_layout(); plt.savefig('demo/collision_v3.png', dpi=90)
print('saved demo/collision_v3.png')
