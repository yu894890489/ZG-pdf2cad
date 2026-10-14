# -*- coding: utf-8 -*-
"""001 塔身中部放大：看清面板腹杆样式"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

axes = json.load(open('demo/axes001_full.json', encoding='utf-8'))
fig, ax = plt.subplots(figsize=(16, 14))
for a in axes:
    zmid = (a['a'][1]+a['b'][1])/2
    if not (18000 <= zmid <= 51000): continue
    if a['ang'] < 2 or a['ang'] > 178: c = 'tab:blue'
    elif 82 < a['ang'] < 98: c = 'tab:red'
    else: c = 'tab:green'
    ax.plot([a['a'][0], a['b'][0]], [a['a'][1], a['b'][1]], color=c, lw=1.2)
ax.set_xlim(-13000, 13000); ax.set_ylim(18000, 51000)
ax.set_aspect('equal'); ax.grid(True, alpha=0.3)
ax.set_xticks(range(-12000, 13000, 2000)); ax.set_yticks(range(18000, 52000, 2000))
plt.tight_layout(); plt.savefig('demo/probe_001_body.png', dpi=110)
print('saved')
