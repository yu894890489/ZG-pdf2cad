# -*- coding: utf-8 -*-
"""探查 004/007/010 的单线图区域：渲染全图 + 提取立面轮廓坐标"""
import sys, os, json, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ezdxf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DXF_DIR = os.path.join('图纸', 'dxf和dwg')

def extract_clean(msp, min_line=5.0, min_vtx=5):
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

for sheet in ('004', '007', '010'):
    f = os.path.join(DXF_DIR, f'37-SA36901S-T0121-{sheet}.dxf')
    doc = ezdxf.readfile(f)
    lines = extract_clean(doc.modelspace())
    fig, ax = plt.subplots(figsize=(20, 12))
    for a, b in lines:
        ax.plot([a[0], b[0]], [a[1], b[1]], color='black', lw=0.3)
    ax.set_title(f'{sheet} overview ({len(lines)} lines)')
    ax.set_aspect('equal')
    plt.tight_layout()
    out = f'demo/probe_{sheet}_overview.png'
    plt.savefig(out, dpi=80)
    plt.close()
    xs = [p[0] for ab in lines for p in ab]; ys = [p[1] for ab in lines for p in ab]
    print(f'{sheet}: {len(lines)} lines, x {min(xs):.0f}~{max(xs):.0f}, y {min(ys):.0f}~{max(ys):.0f} -> {out}')
