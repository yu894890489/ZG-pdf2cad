# -*- coding: utf-8 -*-
"""渲染: 1) 三视图 PNG (matplotlib 正交, 免依赖必成)  2) 真实截面 SCAD
3) OpenSCAD CLI 出真实感 PNG (找到 openscad.exe 才出)  4) STL 实体网格(纯Python, 免依赖)"""
import os, re, sys, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROLE_COLOR = {'LEG': '#2e8b57', 'BR': '#e8821a', 'VG': '#e8821a', 'XB': '#e8821a',
              'DIA': '#4682b4', 'L1': '#dc143c', 'L2': '#ba55d3', 'L3': '#ff1493'}

def _color(mid):
    for pre, c in ROLE_COLOR.items():
        if mid.startswith(pre): return c
    return '#888888'

def _piece_color(m, on):
    """件号对照配色: 有件号=红, 无=黑 (on=成员带 piece_no 字段时启用)"""
    if not on: return _color(m['mid'])
    return '#e02020' if m.get('piece_no') else '#000000'

def three_views(frame_fab, out_png, title=''):
    """正视图 x-z / 侧视图 y-z / 俯视图 x-y, 拆件后坐标;
    成员带件号字段时按匹配着色(红=有件号, 黑=无)"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ms = frame_fab['members']
    by_piece = any('piece_no' in m for m in ms)
    fig, axes = plt.subplots(1, 3, figsize=(21, 8))
    views = [('front x-z', 0, 2), ('side y-z', 1, 2), ('top x-y', 0, 1)]
    for ax, (name, i, j) in zip(axes, views):
        for m in ms:
            p1, p2 = m.get('p1t', m['p1']), m.get('p2t', m['p2'])
            ax.plot([p1[i], p2[i]], [p1[j], p2[j]], color=_piece_color(m, by_piece), lw=0.7)
        ax.set_title(name); ax.set_aspect('equal')
        ax.grid(alpha=0.2)
    if by_piece:
        n_ok = sum(1 for m in ms if m.get('piece_no'))
        fig.text(0.5, 0.005, f'红=有件号对应 {n_ok}/{len(ms)}  黑=未对应', ha='center', fontsize=11)
    if title:
        fig.suptitle(title)
    plt.tight_layout()
    plt.savefig(out_png, dpi=130)
    plt.close(fig)
    return out_png


# ---------------- 真实截面 SCAD ----------------
def _L_centroid(w, t):
    A1, A2 = w * t, t * (w - t)
    A = A1 + A2
    return (A1 * w / 2 + A2 * t / 2) / A, (A1 * t / 2 + A2 * (t + w) / 2) / A

def _roll_for(u):
    import numpy as np
    if abs(u[2]) > 0.999: return 0.0
    z = np.array([0.0, 0.0, 1.0])
    ax = np.cross(z, u); s = np.linalg.norm(ax)
    if s < 1e-9: return 0.0
    ax /= s
    ang = math.atan2(s, u[2])
    x = np.array([1.0, 0.0, 0.0])
    xr = (x * math.cos(ang) + np.cross(ax, x) * math.sin(ang) + ax * (ax @ x) * (1 - math.cos(ang)))
    return math.degrees(math.atan2(-xr[2], np.cross(u, xr)[2]))

def _parse_sec(spec, r_mm):
    m = re.match(r'L(\d{2,3})x(\d{1,2})', spec or '')
    if m: return ('angle', float(m.group(1)), float(m.group(2)))
    m = re.match(r'φ(\d{3})x(\d{1,2})', spec or '')
    if m: return ('tube', float(m.group(1)) / 2, float(m.group(2)))
    return ('tube', r_mm, max(6.0, r_mm / 40))

def real_scad(frame_fab):
    import numpy as np
    ms = frame_fab['members']
    gap = frame_fab['meta'].get('gap_mm', 3.0)
    MAIN = ('LEG', 'BR', 'VG', 'L1', 'L2', 'L3')
    out = [f'// 真实截面模型 (gap={gap}mm)', '$fn = 24;', '$fa = 2;',
           'module angle_sec(w, t, L) {',
           '  linear_extrude(height=L)',
           '    polygon([[0,0],[w,0],[w,t],[t,t],[t,w],[0,w]]); }',
           'module tube_hollow(r, t, L) { difference() { cylinder(h=L, r=r);',
           '  translate([0,0,-1]) cylinder(h=L+2, r=max(r-t,1)); } }']
    for m in ms:
        p1 = np.array(m.get('p1t', m['p1']), float)
        p2 = np.array(m.get('p2t', m['p2']), float)
        v = p2 - p1; L = float(np.linalg.norm(v))
        if L < 1: continue
        u = v / L
        kind = _parse_sec(m.get('spec'), m['r_mm'])
        # 件号对照配色: 有件号=红, 无=黑 (成员带 piece_no 字段时启用)
        if 'piece_no' in m:
            c = '[1,0.08,0.08]' if m.get('piece_no') else '[0.02,0.02,0.02]'
        else:
            c = '[0.75,0.77,0.80]' if m['mid'][:2] in MAIN else '[0.60,0.63,0.67]'
        ang = math.degrees(math.acos(max(-1, min(1, u[2]))))
        ax = np.cross([0, 0, 1], u)
        if np.linalg.norm(ax) < 1e-9: ax = [1.0, 0.0, 0.0]
        axtxt = f'[{ax[0]:.6f},{ax[1]:.6f},{ax[2]:.6f}]'
        head = (f'translate([{p1[0]:.1f},{p1[1]:.1f},{p1[2]:.1f}]) '
                f'rotate(a={ang:.4f},v={axtxt}) ')
        if kind[0] == 'angle':
            _, w, t = kind
            cx, cy = _L_centroid(w, t)
            roll = _roll_for(u)
            out.append(head + f'rotate([0,0,{roll:.2f}]) translate([-{cx:.1f},-{cy:.1f},0]) '
                       f'color({c}) angle_sec({w:.0f},{t:.0f},{L:.1f});  //{m["mid"]} {m.get("spec") or ""}')
        else:
            _, r, t = kind
            out.append(head + f'color({c}) tube_hollow({r:.1f},{t:.1f},{L:.1f});  //{m["mid"]} {m.get("spec") or ""}')
    return '\n'.join(out)


# ---------------- STL 实体网格 (纯 Python, 不依赖 OpenSCAD) ----------------
def _member_frame(u):
    """与 real_scad 的 rotate(a=ang,v=ax) 一致的局部坐标系: 返回 (e1,e2)"""
    import numpy as np
    z = np.array([0.0, 0.0, 1.0])
    ax = np.cross(z, u)
    s = np.linalg.norm(ax)
    if s < 1e-9:
        e1 = np.array([1.0, 0.0, 0.0])
    else:
        ax = ax / s
        ang = math.atan2(s, u[2])
        x = np.array([1.0, 0.0, 0.0])
        e1 = x * math.cos(ang) + np.cross(ax, x) * math.sin(ang) + ax * (ax @ x) * (1 - math.cos(ang))
    return e1, np.cross(u, e1)

def write_stl(frame_fab, out_stl, fn=24):
    """拆件后真实截面二进制 STL: 角钢=2矩形棱柱, 钢管=空心环柱"""
    import numpy as np, struct
    ms = frame_fab['members']
    tris = []

    def _quad(a, b, c, d):
        tris.append((a, b, c)); tris.append((a, c, d))

    for m in ms:
        p1 = np.array(m.get('p1t', m['p1']), float)
        p2 = np.array(m.get('p2t', m['p2']), float)
        v = p2 - p1
        L = float(np.linalg.norm(v))
        if L < 1: continue
        u = v / L
        kind = _parse_sec(m.get('spec'), m['r_mm'])
        roll = _roll_for(u) if kind[0] == 'angle' else 0.0
        e1, e2 = _member_frame(u)
        cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
        E1 = cr * e1 + sr * e2
        E2 = -sr * e1 + cr * e2

        def W(x, y, z):
            return p1 + E1 * x + E2 * y + u * z

        if kind[0] == 'angle':
            _, w, t = kind
            cx, cy = _L_centroid(w, t)
            rects = [((0, 0), (w, 0), (w, t), (0, t)),
                     ((0, t), (t, t), (t, w), (0, w))]
            for rect in rects:
                b0 = [W(x - cx, y - cy, 0) for x, y in rect]
                t0 = [b + u * L for b in b0]
                for k in range(4):
                    _quad(b0[k], b0[(k + 1) % 4], t0[(k + 1) % 4], t0[k])
                tris.append((b0[0], b0[2], b0[1])); tris.append((b0[0], b0[3], b0[2]))  # 底帽 -u
                tris.append((t0[0], t0[1], t0[2])); tris.append((t0[0], t0[2], t0[3]))  # 顶帽 +u
        else:
            _, r, th = kind
            ri = max(r - th, 1.0)
            bo = [W(r * math.cos(2 * math.pi * k / fn), r * math.sin(2 * math.pi * k / fn), 0) for k in range(fn)]
            bi = [W(ri * math.cos(2 * math.pi * k / fn), ri * math.sin(2 * math.pi * k / fn), 0) for k in range(fn)]
            to = [b + u * L for b in bo]
            ti = [b + u * L for b in bi]
            for k in range(fn):
                k2 = (k + 1) % fn
                _quad(bo[k], bo[k2], to[k2], to[k])   # 外侧面
                _quad(bi[k], ti[k2], bi[k2], ti[k])   # 内侧面(法向朝轴)
                _quad(bo[k], bi[k], bi[k2], bo[k2])   # 底环帽 -u
                _quad(to[k], to[k2], ti[k2], ti[k])   # 顶环帽 +u
    with open(out_stl, 'wb') as f:
        f.write(b'tower2model real-section solid'.ljust(80, b' '))
        f.write(struct.pack('<I', len(tris)))
        for a, b, c in tris:
            n = np.cross(b - a, c - a)
            ln = float(np.linalg.norm(n))
            n = n / ln if ln > 1e-12 else np.zeros(3)
            f.write(struct.pack('<3f', *n))
            for p in (a, b, c):
                f.write(struct.pack('<3f', *p))
            f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', 0))
    return len(tris), out_stl


VIEWS = {
    'iso':   (0, 0, 64000, 62, 0, 32, 440000),
    'head':  (9000, 0, 131800, 68, 0, 24, 70000),
    'joint': (12500, 0, 131200, 72, 0, 18, 14000),
}

def views_for(frame, tower=None):
    """OpenSCAD 相机按塔架包围盒自适应(VIEWS 按 SZK 181m 硬编码, 其它塔型会错位);
    builtin 塔型保持原相机不动"""
    if tower == 'SZK31102A':
        return dict(VIEWS)
    xs = [c for m in frame['members'] for c in (m['p1'][0], m['p2'][0])]
    ys = [c for m in frame['members'] for c in (m['p1'][1], m['p2'][1])]
    zs = [c for m in frame['members'] for c in (m['p1'][2], m['p2'][2])]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    h = max(zs) - min(zs)
    zt = max(zs)
    return {
        'iso':   (cx, cy, (min(zs) + zt) / 2, 62, 0, 32, h * 2.4),
        'head':  (cx, cy, zt * 0.92, 68, 0, 24, h * 0.55),
        'joint': (cx, cy, zt * 0.92, 72, 0, 18, h * 0.12),
    }

def openscad_png(scad_path, out_png, view, openscad_exe, imgsize='1600,1200',
                 colorscheme='Starnight'):
    """view: VIEWS 的 key / (vpt3, vpr3, vpd) 元组"""
    import subprocess
    cam = VIEWS.get(view) if view in VIEWS else view
    if cam:
        cx, cy, cz, rx, ry, rz, d = cam
        tag = view if view in VIEWS else 'cam'
        wrapper = scad_path.replace('.scad', f'_view_{tag}.scad')
        with open(wrapper, 'w', encoding='utf-8') as f:
            f.write(f'$vpt=[{cx},{cy},{cz}]; $vpr=[{rx},{ry},{rz}]; $vpd={d};\n'
                    f'include <{os.path.abspath(scad_path).replace(chr(92), "/")}>\n')
        scad_path = wrapper
    r = subprocess.run([openscad_exe, '-o', out_png, scad_path,
                        f'--imgsize={imgsize}', f'--colorscheme={colorscheme}'],
                       capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=600)
    return os.path.exists(out_png)
