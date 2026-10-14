# -*- coding: utf-8 -*-
"""全塔参数化重建: 参数驱动(builtin SZK31102A 表 + 通用解析 params 两用)
塔身: 直线锥腿(轮廓折线) + 横隔 + 腹杆节间(diamond/X/single/K)
横担: 上下弦折线悬臂桁架(可选 W 形头部)
坐标来自 001 正视图轴线提取(已验证); 其他塔型的 params 由 generic_parse 产出
"""
import json, math
from collections import Counter

# ---- SZK31102A 内置参数表(001 基准 v3, 坐标已验证) ----
_SZK31102A_PARAMS = {
    'tower': 'SZK31102A', 'height_mm': 135000.0, 'root_half_mm': 13953.0,
    'note': '001 正视图重建 v3: 菱形/X 腹杆 + W形地线支架 + 芬克式横担',
    'body_profile': [(0.0, 13953.0), (92364.0, 2904.0), (96462.0, 2791.0),
                     (122610.0, 1980.0), (128199.0, 1808.0), (133860.0, 1637.0)],
    'diaphragm_z': [2782.0, 19355.0, 34254.0, 48409.0, 60330.0, 71132.0,
                    92364.0, 104434.0, 133860.0],
    'panels': [{'z0': 19355.0, 'z1': 34254.0, 'type': 'diamond'},
               {'z0': 34254.0, 'z1': 48409.0, 'type': 'diamond'},
               {'z0': 48409.0, 'z1': 60330.0, 'type': 'diamond'},
               {'z0': 60330.0, 'z1': 71132.0, 'type': 'diamond'},
               {'z0': 71132.0, 'z1': 81934.0, 'type': 'diamond'},
               {'z0': 81934.0, 'z1': 92364.0, 'type': 'diamond'},
               {'z0': 92364.0,  'z1': 96461.0,  'type': 'X'},
               {'z0': 96461.0,  'z1': 100558.0, 'type': 'X'},
               {'z0': 100558.0, 'z1': 104434.0, 'type': 'X'},
               {'z0': 104434.0, 'z1': 108232.0, 'type': 'X'},
               {'z0': 108232.0, 'z1': 112032.0, 'type': 'X'},
               {'z0': 112032.0, 'z1': 115832.0, 'type': 'X'},
               {'z0': 115832.0, 'z1': 119630.0, 'type': 'X'},
               {'z0': 119630.0, 'z1': 122610.0, 'type': 'X'},
               {'z0': 122610.0, 'z1': 125442.0, 'type': 'X'},
               {'z0': 125442.0, 'z1': 128199.0, 'type': 'X'},
               {'z0': 128199.0, 'z1': 130880.0, 'type': 'X'},
               {'z0': 130880.0, 'z1': 133860.0, 'type': 'X'}],
    'vg_top': 19355.0,
    'crossarms': [
        {'tag': 'L1',
         'top_pts': [(1700, 133860), (4245, 133484), (6853, 133107), (9125, 132779), (11405, 132498)],
         'bot_pts': [(1700, 130880), (5780, 130880), (7806, 130880), (9831, 130880), (11405, 130880)],
         'sub': [(3753, 130880), (3753, 130880), (2987, 132191), (5011, 132191)],
         'half_root': 1500.0, 'half_tip': 700.0, 'r_chord': 90.0, 'r_web': 55.0,
         'head': {'lines': [((11405, 132498), (16021, 134955)),
                            ((11405, 130880), (16021, 133838)),
                            ((16021, 133838), (16021, 134955)),
                            ((13922, 133838), (17140, 133838))],
                  'zig': [(11405, 132498), (12451, 131535), (12665, 133167), (13497, 132209),
                          (13922, 133838), (14759, 133024), (16021, 134955)],
                  'taper': (11405.0, 17140.0, 700.0, 600.0)}},
        {'tag': 'L2',
         'top_pts': [(2072, 119630), (4690, 118613), (7308, 117597), (9928, 116578)],
         'bot_pts': [(2186, 115832), (6405, 115832), (8490, 115832), (10278, 115832)],
         'sub': [(4296, 115832), (4296, 115832), (3439, 117221), (5546, 117221)],
         'half_root': 1850.0, 'half_tip': 520.0, 'r_chord': 90.0, 'r_web': 55.0},
        {'tag': 'L3',
         'top_pts': [(2534, 104434), (5181, 103390), (7828, 102347), (10475, 101303)],
         'bot_pts': [(2658, 100558), (6777, 100558), (8789, 100558), (10799, 100558)],
         'sub': [(4714, 100558), (4714, 100558), (3916, 101974), (5979, 101974)],
         'half_root': 2000.0, 'half_tip': 550.0, 'r_chord': 90.0, 'r_web': 55.0},
    ],
}


def _make_add(members):
    _n = [0]
    def add(role, p1, p2, r, spec='参数化', mid_prefix='M'):
        _n[0] += 1
        members.append({'mid': f'{mid_prefix}{_n[0]:04d}', 'role': role, 'spec': spec,
                        'r_mm': r, 'p1': [round(p1[0],1), round(p1[1],1), round(p1[2],1)],
                        'p2': [round(p2[0],1), round(p2[1],1), round(p2[2],1)]})
    return add


def _hw_fn(profile):
    """轮廓折线 -> 半宽插值函数 hw(z)(段内线性, 越界夹取)"""
    pts = sorted([(float(z), float(w)) for z, w in profile])
    def hw(z):
        if z <= pts[0][0]:
            return pts[0][1]
        for (z0, w0), (z1, w1) in zip(pts, pts[1:]):
            if z0 <= z <= z1:
                return w0 + (w1-w0)*(z-z0)/(z1-z0)
        return pts[-1][1]
    return hw


def _face_p(hw, face):
    if face == 0:   return lambda u, z: (u,  hw(z), z)
    elif face == 1: return lambda u, z: (u, -hw(z), z)
    elif face == 2: return lambda u, z: ( hw(z), u, z)
    else:           return lambda u, z: (-hw(z), u, z)


def _build_crossarm(add, ca):
    """横担悬臂桁架。raw_segs 存在时为图面矢量直通(线段原样进模, ±y 前后两片,
    保留真实塔头形状); 否则参数化: 上下弦折线 + W 腹杆 + 次腹杆 + 横隔 + 端部,
    镜像 ±x ±y"""
    tag = ca['tag']
    raw = ca.get('raw_segs')
    if raw:
        d = ca.get('half_root', 700.0)
        lens = sorted(math.hypot(s[2]-s[0], s[3]-s[1]) for s in raw)
        lthr = lens[max(0, int(len(lens)*0.3))] if lens else 0.0
        for (xa, za, xb, zb) in raw:
            chord = math.hypot(xb-xa, zb-za) >= lthr
            for sy in (1, -1):
                add(f'{tag}上弦' if chord else f'{tag}W腹杆',
                    (xa, sy*d, za), (xb, sy*d, zb),
                    ca.get('r_chord', 90.0) if chord else ca.get('r_web', 55.0),
                    '横担主材' if chord else '斜材', tag)
        return
    top_pts, bot_pts = ca['top_pts'], ca['bot_pts']
    sub = ca.get('sub')
    half_root, half_tip = ca['half_root'], ca['half_tip']
    r_chord = ca.get('r_chord', 90.0); r_web = ca.get('r_web', 55.0)
    reach = bot_pts[-1][0] - bot_pts[0][0]
    x_root = bot_pts[0][0]
    def yh(x):
        t = max(0.0, min(1.0, (x - x_root)/reach))
        return half_root + (half_tip-half_root)*t
    for sx in (1,-1):
        X = lambda v: sx*v
        for sy in (1,-1):
            Y = lambda v: sy*v
            for pts, role, rc in ((top_pts, f'{tag}上弦', r_chord), (bot_pts, f'{tag}下弦', r_chord)):
                for (x0,z0),(x1,z1) in zip(pts, pts[1:]):
                    add(role, (X(x0),Y(yh(x0)),z0), (X(x1),Y(yh(x1)),z1), rc, '横担主材', tag)
            seq = []
            for i in range(1, len(top_pts)):
                seq.append(('top', i))
                if i-1 < len(bot_pts)-1 and i < len(bot_pts):
                    seq.append(('bot', i))
            prev = ('bot', 0)
            for kind, i in seq:
                pts, x, z = (top_pts, top_pts[i][0], top_pts[i][1]) if kind=='top' else (bot_pts, bot_pts[i][0], bot_pts[i][1])
                px, pz = (top_pts[prev[1]][0], top_pts[prev[1]][1]) if prev[0]=='top' else (bot_pts[prev[1]][0], bot_pts[prev[1]][1])
                add(f'{tag}W腹杆', (X(px),Y(yh(px)),pz), (X(x),Y(yh(x)),z), r_web, '斜材', tag)
                prev = (kind, i)
            if sub:
                (xs1, zs1), (xs2, zs2), (xh1, zh), (xh2, zh2) = sub
                add(f'{tag}次腹杆', (X(xs1),Y(yh(xs1)),zs1), (X(xh1),Y(yh(xh1)),zh), 45.0, '斜材', tag)
                add(f'{tag}次腹杆', (X(xs1),Y(yh(xs1)),zs1), (X(xh2),Y(yh(xh2)),zh), 45.0, '斜材', tag)
                add(f'{tag}次腹杆', (X(xh1),Y(yh(xh1)),zh), (X(xh2),Y(yh(xh2)),zh), 45.0, '横材', tag)
            for pts in (top_pts, bot_pts):
                for (x, z) in pts[1:-1]:
                    add(f'{tag}横隔', (X(x),-Y(yh(x)),z), (X(x),Y(yh(x)),z), 45.0, '横隔', tag)
        xt, zt = top_pts[-1]; xb, zb = bot_pts[-1]
        for sy in (1,-1):
            add(f'{tag}端斜杆', (X(xt),sy*yh(xt),zt), (X(xb),sy*yh(xb),zb), 60.0, '横担主材', tag)
        add(f'{tag}端横梁', (X(xb),-yh(xb),zb), (X(xb),yh(xb),zb), 60.0, '横隔', tag)
    # 可选 W 形头部(地线支架等)
    head = ca.get('head')
    if head:
        x_a, x_b, w_a, w_b = head.get('taper', (top_pts[-1][0], top_pts[-1][0]*1.5,
                                                half_tip, half_tip*0.85))
        def yh2(x):
            t = (abs(x)-x_a)/max(1e-9, (x_b-x_a))
            return w_a - (w_a-w_b)*t
        for sx in (1, -1):
            X = lambda v: sx*v
            for (a, b) in head.get('lines', []):
                for sy in (1,-1):
                    add(f'{tag}头弦', (X(a[0]), sy*yh2(a[0]), a[1]), (X(b[0]), sy*yh2(b[0]), b[1]),
                        60.0, '横担主材', tag)
            zig = head.get('zig', [])
            for (a, b) in zip(zig, zig[1:]):
                for sy in (1,-1):
                    add(f'{tag}头腹杆', (X(a[0]), sy*yh2(a[0]), a[1]), (X(b[0]), sy*yh2(b[0]), b[1]),
                        45.0, '斜材', tag)


def build_frame_from_params(P):
    """params -> frame。params 见 _SZK31102A_PARAMS / generic_parse 输出 schema"""
    members = []
    add = _make_add(members)
    hw = _hw_fn(P['body_profile'])

    # ---- 塔身主材 ----
    prof = sorted([(float(z), float(w)) for z, w in P['body_profile']])
    for sx in (1,-1):
        for sy in (1,-1):
            for (z0,w0),(z1,w1) in zip(prof, prof[1:]):
                add('塔身主材', (sx*w0, sy*w0, z0), (sx*w1, sy*w1, z1), 160.0, '主材', 'LEG')

    # ---- 横隔 ----
    for z in P.get('diaphragm_z', []):
        w = hw(z)
        corners = [(sx*w, sy*w, z) for sx in (1,-1) for sy in (1,-1)]
        for i, j in ((0,1),(0,2),(1,3),(2,3)):
            add('横隔横材', corners[i], corners[j], 55.0, '横隔', 'DIA')

    # ---- 腹杆节间(按 z0 排序, 与 builtin 双表顺序一致) ----
    for pan in sorted(P.get('panels', []), key=lambda p: p['z0']):
        z0, z1 = float(pan['z0']), float(pan['z1'])
        typ = pan.get('type', 'X')
        if typ == 'diamond':
            zm = (z0+z1)/2.0; wm = hw(zm)
            for face in range(4):
                p = _face_p(hw, face)
                for sgn in (1, -1):
                    add('菱形斜材', p(0.0, z0), p(sgn*wm, zm), 60.0, '斜材', 'BR')
                    add('菱形斜材', p(sgn*wm, zm), p(0.0, z1), 60.0, '斜材', 'BR')
        elif typ == 'X':
            w0, w1 = hw(z0), hw(z1)
            for face in range(4):
                p = _face_p(hw, face)
                add('X斜材', p(-w0, z0), p(w1, z1), 60.0, '斜材', 'XB')
                add('X斜材', p(w0, z0), p(-w1, z1), 60.0, '斜材', 'XB')
        elif typ == 'single':
            w0, w1 = hw(z0), hw(z1)
            for face in range(4):
                p = _face_p(hw, face)
                if face % 2 == 0:
                    add('单斜材', p(-w0, z0), p(w1, z1), 60.0, '斜材', 'BR')
                else:
                    add('单斜材', p(w0, z0), p(-w1, z1), 60.0, '斜材', 'BR')
        elif typ == 'K':
            w0, w1 = hw(z0), hw(z1); zm = (z0+z1)/2.0
            for face in range(4):
                p = _face_p(hw, face)
                add('K斜材', p(-w0, z0), p(0.0, zm), 60.0, '斜材', 'XB')
                add('K斜材', p(w0, z0), p(0.0, zm), 60.0, '斜材', 'XB')
                add('K斜材', p(0.0, zm), p(w1, z1), 60.0, '斜材', 'XB')
                add('K斜材', p(0.0, zm), p(-w1, z1), 60.0, '斜材', 'XB')
        # 'none'/未知类型: 该节间不生成腹杆

    # ---- 人字撑(可选) ----
    vg_top = P.get('vg_top')
    if vg_top:
        for face in range(4):
            p = _face_p(hw, face)
            w_bottom = hw(0.0)
            add('人字撑', p(-w_bottom, 0.0), p(0.0, vg_top), 80.0, '斜材', 'VG')
            add('人字撑', p(w_bottom, 0.0), p(0.0, vg_top), 80.0, '斜材', 'VG')

    # ---- 横担 ----
    for ca in P.get('crossarms', []):
        _build_crossarm(add, ca)

    return {'meta': {
                'tower': P.get('tower', 'UNKNOWN'),
                'height_mm': P.get('height_mm', max(z for z, _ in prof)),
                'root_half_mm': P.get('root_half_mm', prof[0][1]),
                'note': P.get('note', '参数化重建')},
            'members': members}


def build_frame():
    """内置 SZK31102A(001 基准 v3)"""
    return build_frame_from_params(_SZK31102A_PARAMS)


def to_scad(frame):
    """轴线着色 SCAD (杆身圆柱直杆)"""
    def sv(p): return f"[{p[0]:.0f}, {p[1]:.0f}, {p[2]:.0f}]"
    def col(mid):
        for pre, c in (('LEG', 'ForestGreen'), ('BR', 'DarkOrange'), ('VG', 'DarkOrange'),
                       ('XB', 'DarkOrange'), ('DIA', 'SteelBlue'), ('L1', 'Crimson'),
                       ('L2', 'MediumOrchid'), ('L3', 'DeepPink')):
            if mid.startswith(pre): return c
        return 'Gray'
    tower = frame.get('meta', {}).get('tower', 'SZK31102A')
    out = [f'// {tower} 全塔 (参数化重建)',
           '$fn=24;', '',
           'module tube(p1,p2,r,col){v=p2-p1;L=norm(v);ax=cross([0,0,1],v);translate(p1)color(col)if(norm(ax)<1e-9)rotate([0,v[2]>0?0:180,0])cylinder(h=L,r=r);else rotate(a=acos(min(1,max(-1,v[2]/L))),v=ax)cylinder(h=L,r=r);}', '']
    for m in frame['members']:
        out.append(f'tube({sv(m["p1"])},{sv(m["p2"])},{m["r_mm"]:.0f},"{col(m["mid"])}");')
    return '\n'.join(out)
