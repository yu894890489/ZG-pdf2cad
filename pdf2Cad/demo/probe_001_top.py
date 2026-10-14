# -*- coding: utf-8 -*-
"""001 顶部区域放大：看地线支架 W 形 + 三层横担立面轮廓"""
import sys, os, json, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

d1 = json.load(open('demo/data001.json', encoding='utf-8'))
CX, Y_BOT, SC = 624.0, 3749.0, 135000.0/3632.0

def to_mm(x, y):
    return (x-CX)*SC, (Y_BOT-y)*SC

# 顶部: z 95000~137000 → y_pt 2734~3749-... 取 y_pt 100~290, x 380~870
fig, ax = plt.subplots(figsize=(20, 12))
for ln in d1['lines']:
    (xa, ya), (xb, yb) = ln['a'], ln['b']
    mx = (xa+xb)/2; my = (ya+yb)/2
    if 350 <= mx <= 900 and 90 <= my <= 300:
        X1, Z1 = to_mm(xa, ya); X2, Z2 = to_mm(xb, yb)
        ax.plot([X1, X2], [Z1, Z2], color='black', lw=0.5)
for c in d1.get('circles', []):
    mx, my = c['c'][0], c['c'][1]
    if 350 <= mx <= 900 and 90 <= my <= 300:
        X, Z = to_mm(mx, my)
        ax.add_patch(plt.Circle((X, Z), c['r']*SC, fill=False, lw=0.4))
ax.set_aspect('equal'); ax.grid(True, alpha=0.3)
ax.set_title('001 top region (mm): ground wire support + 3 crossarms')
plt.tight_layout(); plt.savefig('demo/probe_001_top.png', dpi=100)
print('saved demo/probe_001_top.png')
