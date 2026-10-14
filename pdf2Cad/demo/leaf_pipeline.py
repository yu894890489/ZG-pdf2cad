# -*- coding: utf-8 -*-
"""叶节点处理流水线模板：单个DXF → 干净几何 → 轴线 → 节点图 → 3D 子模型
可对任意部段图/横担图复用。"""
import sys, os, json, math, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from collections import Counter
import ezdxf

def process_leaf(dxf_path, out_name, z_base=0.0, scale=30.0, min_line=5.0, min_vtx=5):
    """处理单个 DXF 叶节点
    Args:
        dxf_path: DXF 文件路径
        out_name: 输出名称（如 'L2_crossarm', 'body_seg_013'）
        z_base: 该叶节点在塔中的 z 标高基准
        scale: 图纸比例（1:30 → 30）
        min_line: 最小线长(mm on page)
        min_vtx: 最小多段线顶点数
    Returns:
        dict with members, axes, circles, stats
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # ---- 1. 过滤：HATCH/POINT/SOLID/碎线/碎多段线 ----
    clean_lines = []   # LINE + LWPOLYLINE拆分线段
    circles = []       # CIRCLE
    n_total = 0
    n_deleted = 0

    for e in msp:
        n_total += 1
        t = e.dxftype()
        if t in ('HATCH', 'SOLID', 'POINT'):
            n_deleted += 1
        elif t == 'LINE':
            L = e.dxf.start.distance(e.dxf.end)
            if L > min_line:
                clean_lines.append({
                    'a': [e.dxf.start.x, e.dxf.start.y],
                    'b': [e.dxf.end.x, e.dxf.end.y], 'len': L})
            else:
                n_deleted += 1
        elif t == 'LWPOLYLINE':
            pts = e.get_points('xy')
            if len(pts) > min_vtx:
                for i in range(len(pts) - 1):
                    d = math.dist(pts[i][:2], pts[i+1][:2])
                    if d > min_line:
                        clean_lines.append({
                            'a': list(pts[i][:2]), 'b': list(pts[i+1][:2]), 'len': d})
            else:
                n_deleted += 1
        elif t == 'CIRCLE':
            circles.append({'c': [e.dxf.center.x, e.dxf.center.y], 'r': e.dxf.radius})
        elif t in ('ARC', 'SPLINE', 'ELLIPSE'):
            pass  # 保留但暂不处理

    # ---- 2. 共线聚类 → 轴线 ----
    n = len(clean_lines)
    parent = list(range(n))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    P = []
    for c in clean_lines:
        dx, dy = c['b'][0]-c['a'][0], c['b'][1]-c['a'][1]
        L = math.hypot(dx, dy) or 1
        P.append((dx/L, dy/L, c['a'][0], c['a'][1], L))
    def colinear(i, j):
        uxi, uyi, axi, ayi, Li = P[i]
        uxj, uyj, axj, ayj, Lj = P[j]
        dot = uxi*uxj + uyi*uyj
        if abs(dot) < 0.9985: return False
        if dot < 0: uxj, uyj = -uxj, -uyj
        perp = abs(uxj*(ayi-ayj) - uyj*(axi-axj))
        if perp > 2.5: return False
        t1 = (axj-axi)*uxi + (ayj-ayi)*uyi
        return (t1+Lj) > -4 and t1 < Li+4
    buckets = {}
    for i, c in enumerate(clean_lines):
        ang = round(math.degrees(math.atan2(P[i][1], P[i][0])) % 180 / 3)
        buckets.setdefault(ang, []).append(i)
    for key, idxs in buckets.items():
        for bi in range(len(idxs)):
            for bj in range(bi+1, len(idxs)):
                i, j = idxs[bi], idxs[bj]
                ri, rj = find(i), find(j)
                if ri != rj and colinear(i, j): parent[rj] = ri
    groups = {}
    for i in range(n): groups.setdefault(find(i), []).append(i)

    axes = []
    for idxs in groups.values():
        uxi, uyi, ox, oy, _ = P[idxs[0]]
        if uxi < 0: uxi, uyi = -uxi, -uyi
        ts = []
        for i in idxs:
            for p in (clean_lines[i]['a'], clean_lines[i]['b']):
                ts.append((p[0]-ox)*uxi + (p[1]-oy)*uyi)
        t0, t1 = min(ts), max(ts)
        ext = t1 - t0
        if ext < 15: continue  # 最短轴线 15mm page = 450mm real
        axes.append({
            'a': [ox+uxi*t0, oy+uyi*t0], 'b': [ox+uxi*t1, oy+uyi*t1],
            'ext': ext, 'nseg': len(idxs),
            'ang': round(math.degrees(math.atan2(uyi, uxi)) % 180, 1)})

    # ---- 3. 节点图 ----
    nodes = []
    def snap(p, tol=4.0):
        for i, q in enumerate(nodes):
            if math.dist(p, q) < tol: return i
        nodes.append(list(p)); return len(nodes) - 1
    members = []
    def add_mem(p1, p2, role, r):
        i1, i2 = snap(p1), snap(p2)
        if i1 == i2: return
        members.append({'n1': i1, 'n2': i2, 'role': role, 'r_mm': r})
    for ax in axes:
        add_mem(ax['a'], ax['b'], '杆件', 80.0)

    return {
        'out_name': out_name,
        'stats': {
            'total_entities': n_total,
            'deleted_debris': n_deleted,
            'clean_lines': len(clean_lines),
            'axes': len(axes),
            'circles': len(circles),
            'nodes': len(nodes),
            'members': len(members),
        },
        'axes': axes,
        'circles': circles,
        'nodes': nodes,
        'members': members,
        'clean_lines': clean_lines,
    }


if __name__ == '__main__':
    import ezdxf
    DXF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           '图纸', 'dxf和dwg')

    # 测试：处理 008
    f = os.path.join(DXF_DIR, '37-SA36901S-T0121-008.dxf')
    r = process_leaf(f, 'test_008')
    print(json.dumps(r['stats'], indent=2, ensure_ascii=False))
