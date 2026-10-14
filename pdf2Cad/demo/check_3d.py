# -*- coding: utf-8 -*-
"""3D 视角检查: 横担立体形态"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Line3DCollection

f = json.load(open('demo/frame.json', encoding='utf-8'))
ms = f['members']

fig = plt.figure(figsize=(18, 8))
views = [(20, -60, 'iso top'), (8, -85, 'low front-left'), (15, 130, 'rear iso')]
for vi, (elev, azim, title) in enumerate(views):
    ax = fig.add_subplot(1, 3, vi+1, projection='3d')
    for m in ms:
        p1, p2, mid = m['p1'], m['p2'], m['mid']
        c = 'gray'
        if mid.startswith('LEG'): c = 'forestgreen'
        elif mid.startswith(('BR','XB','VG')): c = 'darkorange'
        elif mid.startswith('DIA'): c = 'steelblue'
        elif mid.startswith('L1'): c = 'crimson'
        elif mid.startswith('L2'): c = 'mediumorchid'
        elif mid.startswith('L3'): c = 'deeppink'
        ax.plot([p1[0],p2[0]],[p1[1],p2[1]],[p1[2],p2[2]], color=c, lw=0.7)
    ax.set_box_aspect((36000, 36000, 140000))
    ax.view_init(elev=elev, azim=azim)
    ax.set_title(title)
    ax.set_axis_off()
plt.tight_layout(); plt.savefig('demo/check_3d_v3.png', dpi=90)
print('saved demo/check_3d_v3.png')
