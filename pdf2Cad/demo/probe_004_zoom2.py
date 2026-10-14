# -*- coding: utf-8 -*-
"""放大 004 底部视图 + 中心下平面视图"""
import sys, os, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ezdxf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DXF_DIR = os.path.join('图纸', 'dxf和dwg')

def extract_clean(msp, min_line=2.0, min_vtx=4):
    lines = []
    for e in msp:
        t = e.dxftype()
        if t == 'LINE':
            L = e.dxf.start.distance(e.dxf.end)
            if L > min_line:
                lines.append(([e.dxf.start.x, e.dxf.start.y], [e.dxf.end.x, e.dxf.end.y]))
        elif t == 'LWPOLYLINE':
            pts = e.get_points('xy')
            if len(pts) > min_vtx:
                for i in range(len(pts)-1):
                    d = math.dist(pts[i][:2], pts[i+1][:2])
                    if d > min_line:
                        lines.append((list(pts[i][:2]), list(pts[i+1][:2])))
    return lines

doc = ezdxf.readfile(os.path.join(DXF_DIR, '37-SA36901S-T0121-004.dxf'))
lines = extract_clean(doc.modelspace())

def crop(x0, x1, y0, y1, out, arrows=False):
    fig, ax = plt.subplots(figsize=(18, 7))
    for a, b in lines:
        mx, my = (a[0]+b[0])/2, (a[1]+b[1])/2
        if x0 <= mx <= x1 and y0 <= my <= y1:
            ax.plot([a[0], b[0]], [a[1], b[1]], color='black', lw=0.6)
    ax.set_aspect('equal'); ax.grid(True, alpha=0.3)
    plt.tight_layout(); plt.savefig(out, dpi=110); plt.close()
    print('saved', out)

crop(40, 340, 30, 145, 'demo/probe_004_bottom.png')
crop(40, 430, 180, 480, 'demo/probe_004_center.png')
