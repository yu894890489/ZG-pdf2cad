# -*- coding: utf-8 -*-
"""真实感渲染 v1 (2026-09-30): frame_fab.json -> tower_frame_real.scad
型材按真实截面:
  - 角钢 L{w}x{t}: L 形多边形沿轴线挤出, 质心对齐轴线(与 stick 模型端点连续),
    滚转角自动取一肢尽量水平( numpy 解 phi=atan2(-x'z,(u×x')z) )
  - 钢管 φ{d}x{t}: 空心圆管(外径 d 壁厚 t), 端头切口可见环形断面
配色: 镀锌钢两档(主材亮/辅材暗), 地面半透明圆盘
视角: --views full,head,joint 生成 wrapper scad, 由 openscad CLI 出 PNG
"""
import sys, os, json, re, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np

def L_centroid(w, t):
    A1, A2 = w * t, t * (w - t)
    A = A1 + A2
    cx = (A1 * w / 2 + A2 * t / 2) / A
    cy = (A1 * t / 2 + A2 * (t + w) / 2) / A
    return cx, cy

def roll_for(u):
    """滚转角(deg)使角钢一肢尽量水平; 竖直杆返回 0"""
    if abs(u[2]) > 0.999: return 0.0
    z = np.array([0.0, 0.0, 1.0])
    ax = np.cross(z, u); s = np.linalg.norm(ax)
    if s < 1e-9: return 0.0
    ax /= s
    ang = math.atan2(s, u[2])
    # Rodrigues: R*z? 直接构造 R 作用在 x 上
    x = np.array([1.0, 0.0, 0.0])
    xr = (x * math.cos(ang) + np.cross(ax, x) * math.sin(ang) +
          ax * (ax @ x) * (1 - math.cos(ang)))
    wz = np.cross(u, xr)[2]
    return math.degrees(math.atan2(-xr[2], wz))

def parse_sec(spec, r_mm):
    """返回 ('angle', w, t) | ('tube', r, t)"""
    m = re.match(r'L(\d{2,3})x(\d{1,2})', spec or '')
    if m: return ('angle', float(m.group(1)), float(m.group(2)))
    m = re.match(r'φ(\d{3})x(\d{1,2})', spec or '')
    if m: return ('tube', float(m.group(1)) / 2, float(m.group(2)))
    return ('tube', r_mm, max(6.0, r_mm / 40))

def main():
    fab = json.load(open('demo/frame_fab.json', encoding='utf-8'))
    ms = fab['members']
    gap = fab['meta'].get('gap_mm', 3.0)
    out = [f'// 真实感渲染 (gap={gap}mm, 截面=真实型材) {len(ms)} members',
           '$fn = 24;', '$fa = 2;',
           'module angle_sec(w, t, L) {',
           '  linear_extrude(height=L)',
           '    polygon([[0,0],[w,0],[w,t],[t,t],[t,w],[0,w]]); }',
           'module tube_hollow(r, t, L) { difference() { cylinder(h=L, r=r);',
           '  translate([0,0,-1]) cylinder(h=L+2, r=max(r-t,1)); } }',
           '// 地面',
           'translate([0,0,-50]) %cylinder(h=50, r=32000);', '']
    # 主材/辅材两档镀锌灰
    MAIN = ('LEG', 'BR', 'VG', 'L1', 'L2', 'L3')
    n_a = n_t = 0
    for m in ms:
        p1 = np.array(m['p1t'], float); p2 = np.array(m['p2t'], float)
        v = p2 - p1; L = float(np.linalg.norm(v))
        if L < 1: continue
        u = v / L
        kind = parse_sec(m['spec'], m['r_mm'])
        c = 'G锌' if m['mid'][:2] in MAIN or m['mid'][:3] in MAIN else 'G锌2'
        if kind[0] == 'angle':
            _, w, t = kind
            cx, cy = L_centroid(w, t)
            roll = roll_for(u)
            ang = math.degrees(math.acos(max(-1, min(1, u[2]))))
            ax = np.cross([0, 0, 1], u)
            if np.linalg.norm(ax) < 1e-9: ax = [1.0, 0.0, 0.0]
            axtxt = f'[{ax[0]:.6f},{ax[1]:.6f},{ax[2]:.6f}]'
            out.append(
                f'translate([{p1[0]:.1f},{p1[1]:.1f},{p1[2]:.1f}]) '
                f'rotate(a={ang:.4f},v={axtxt}) rotate([0,0,{roll:.2f}]) '
                f'translate([-{cx:.1f},-{cy:.1f},0]) '
                f'color({c}) angle_sec({w:.0f},{t:.0f},{L:.1f});  //{m["mid"]} {m["spec"] or ""}')
            n_a += 1
        else:
            _, r, t = kind
            ang = math.degrees(math.acos(max(-1, min(1, u[2]))))
            ax = np.cross([0, 0, 1], u)
            if np.linalg.norm(ax) < 1e-9: ax = [1.0, 0.0, 0.0]
            axtxt = f'[{ax[0]:.6f},{ax[1]:.6f},{ax[2]:.6f}]'
            out.append(
                f'translate([{p1[0]:.1f},{p1[1]:.1f},{p1[2]:.1f}]) '
                f'rotate(a={ang:.4f},v={axtxt}) '
                f'color({c}) tube_hollow({r:.1f},{t:.1f},{L:.1f});  //{m["mid"]} {m["spec"] or ""}')
            n_t += 1
    out.append(f'// 角钢 {n_a}, 钢管 {n_t}')
    open('demo/tower_frame_real.scad', 'w', encoding='utf-8').write('\n'.join(out))
    # 颜色定义
    scad = '\n'.join(out)
    scad = scad.replace('G锌2', 'Gzinc2').replace('G锌', 'Gzinc')
    scad = scad.replace('Gzinc2', '[0.60,0.63,0.67]').replace('Gzinc', '[0.75,0.77,0.80]')
    open('demo/tower_frame_real.scad', 'w', encoding='utf-8').write(scad)
    print(f'tower_frame_real.scad: 角钢 {n_a} + 钢管 {n_t} (gap={gap})')

VIEWS = {
    'full':  (0, 0, 64000, 62, 0, 32, 440000),
    'head':  (9000, 0, 131800, 68, 0, 24, 70000),
    'joint': (12500, 0, 131200, 72, 0, 18, 14000),
}

def make_views(which):
    for name in which:
        cx, cy, cz, rx, ry, rz, d = VIEWS[name]
        s = (f'$vpt=[{cx},{cy},{cz}]; $vpr=[{rx},{ry},{rz}]; $vpd={d};\n'
             f'include <tower_frame_real.scad>\n')
        open(f'demo/view_{name}.scad', 'w', encoding='utf-8').write(s)
        print(f'demo/view_{name}.scad')

if __name__ == '__main__':
    main()
    make_views(sys.argv[1].split(',') if len(sys.argv) > 1 else ['full', 'head', 'joint'])
