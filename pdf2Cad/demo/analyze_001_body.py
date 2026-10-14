# -*- coding: utf-8 -*-
"""分析 001 全塔轴线：silhouette hw(z) 采样 + 面板水平层 + 斜材清单"""
import sys, json, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from collections import defaultdict

axes = json.load(open('demo/axes001_full.json', encoding='utf-8'))

H = [a for a in axes if a['ang'] < 2 or a['ang'] > 178]
V = [a for a in axes if 85 < a['ang'] < 95]
D = [a for a in axes if (2 <= a['ang'] <= 85 or 95 <= a['ang'] <= 178)]

# ---- 1. silhouette hw(z)：斜材端点分箱 ----
samples = defaultdict(list)
for a in D:
    if a['ext'] < 2500: continue
    for p in (a['a'], a['b']):
        z = p[1]
        if 0 <= z <= 93500:
            samples[round(z/600)].append(abs(p[0]))
hw_samp = {}
for k, xs in sorted(samples.items()):
    hw_samp[k*600] = max(xs)
print('hw(z) samples (from diagonal endpoints):')
for z, w in sorted(hw_samp.items()):
    print(f'  z={z:>7}  hw={w:>8.0f}')

# ---- 2. 水平轴线（面板横材）----
print('\nhorizontal axes z 0~128000 (ext>600):')
for a in sorted(H, key=lambda a: a['a'][1]):
    z = a['a'][1]
    if z > 128000: continue
    x0, x1 = sorted([a['a'][0], a['b'][0]])
    print(f"  z={z:>7}  x {x0:>8}~{x1:>8} ext={a['ext']:>6} n={a['nseg']}")

# ---- 3. 斜材清单（塔身区）----
print('\ndiagonal axes z 0~93000 (ext>1500):', len([a for a in D if a['ext']>1500]))
for a in sorted(D, key=lambda a: min(a['a'][1], a['b'][1])):
    z0 = min(a['a'][1], a['b'][1])
    if z0 > 93000 or a['ext'] < 1500: continue
    print(f"  ({a['a'][0]:>7},{a['a'][1]:>7})->({a['b'][0]:>7},{a['b'][1]:>7}) ext={a['ext']:>6} ang={a['ang']:>5} n={a['nseg']}")
