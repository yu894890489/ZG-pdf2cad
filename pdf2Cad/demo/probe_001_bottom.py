# -*- coding: utf-8 -*-
"""001 底部 z<22000 放大渲染"""
import sys, json, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

axes = json.load(open('demo/axes001_full.json', encoding='utf-8'))
fig, ax = plt.subplots(figsize=(16, 10))
for a in axes:
    if min(a['a'][1], a['b'][1]) > 23000: continue
    if a['ang'] < 2 or a['ang'] > 178:
        c = 'tab:blue'
    elif 85 < a['ang'] < 95:
        c = 'tab:red'
    else:
        c = 'tab:green'
    ax.plot([a['a'][0], a['b'][0]], [a['a'][1], a['b'][1]], color=c, lw=1.0)
    ax.annotate(f"{a['ext']:.0f}", xy=((a['a'][0]+a['b'][0])/2, (a['a'][1]+a['b'][1])/2), fontsize=5, color='gray')
ax.set_xlim(-17000, 17000); ax.set_ylim(-500, 23000)
ax.set_aspect('equal'); ax.grid(True, alpha=0.3)
plt.tight_layout(); plt.savefig('demo/probe_001_bottom.png', dpi=110)
print('saved')
