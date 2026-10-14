# -*- coding: utf-8 -*-
"""变体生成器 v2 (根开精化 2026-09-30): SZK31102A 呼高 90~135(16档) x 等长接腿 0/1.5/3/4.5(4档)

【根开精化结论】(依据 001 根开表 64 格完整 OCR + 青色根开标注 + v3 剖面核验)
  1. 001 根开表(右上, 表头"铁塔半根开/基础半根开", 两列数值恒等):
        半根开(H,L) = 18780 - 120*(135-H+L)  mm   —— 64 格逐格吻合
     全根开 = 2x表值。青色标注 37560/36840 即 135/132 呼高的全根开(2x18780/2x18420)。
  2. 呼高 H = 呼称高 = 地面~下导线横担挂点高度(注释3"呼称高范围90~135m")。
     图面塔即 99.0m呼高 级(挂点标高 99152); 塔全高 = H*1000 + 34708(挂点~塔顶)。
     001 正视图底部 ±13988 扇形线是 8 个变体接腿的压缩示意(压缩~0.745),
     青色尺寸线端点落在图面足点上但文字为真值 —— 图面足点宽 ≠ 根开。
  3. 表值与 v3 剖面自洽: 半根开(H,0) = v3坡度线外推到本体底截面以下 4.37m 处宽度
     (16 行核验偏差<=18mm), 即真实塔脚存在约 0.5m(半宽)的塔脚扩大段, 粗略级并入根开。
  4. 变体几何: 塔全高 = H+34.708m; 本体 = v3 沿 z_v3 = 99152-H*1000+L*1000 截剪并平移
     (挂点恒落在 H*1000); 接腿(L>0)从地面半根开向本体底截面 hw_v3(z0) 张开(向外!);
     H>99 时本体比图面高, 按 0.1347 坡度(表值根开->v3底宽)合成下延段(φ660主材+X撑+横隔)。
  5. L=0 塔模型底宽沿用 v3 截面宽(=表值半根开-约520, 腿轮廓线vs中心线), meta.root 报表值全根开。

输出: demo/variants/*.scad (64个) + demo/variants_summary.csv
"""
import sys, os, json, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
sys.path.insert(0, 'demo')
from fabricate import apply_gaps, GAP_MM   # 连接缝隙拆件 (默认3mm, 改 fab.GAP_MM 或此处传参)

frame = json.load(open('demo/frame.json', encoding='utf-8'))
V3 = frame['members']

H_BASE = 99.152          # v3 图面塔的挂点高 m
TOP_SEG = 34708.0        # 挂点~塔顶 mm (133860-99152)
V3_HANG = 99152.0        # v3 挂点标高 mm

def hw_v3(z):
    """v3 本体半宽包络(mm); z<0 线性外推(坡度0.1196)"""
    if z <= 92364:
        return 13953.0 + (2904.0-13953.0) * z/92364.0
    pts = [(92364,2904),(96462,2791),(122610,1980),(128199,1808),(133860,1637)]
    for (z0,w0),(z1,w1) in zip(pts, pts[1:]):
        if z0 <= z <= z1:
            return w0 + (w1-w0)*(z-z0)/(z1-z0)
    return 1637.0

def half_root(H, L):
    """001 根开表: 半根开 = 18780 - 120*(135-H+L) mm (64格实测)"""
    return 18780.0 - 120.0*(135.0-H+L)

ANGLE_W = {'L45x4':2.74,'L63x5':4.82,'L75x5':5.82,'L75x6':6.91,'L100x7':10.83,
           'L110x7':11.93,'L125x8':15.50,'L160x10':24.34}
TUBE_W = {'φ550x12':159.57, 'φ660x14':223.39}
def unit_w(spec): return ANGLE_W.get(spec) or TUBE_W.get(spec)

def spec_for(mid, role, z):
    if mid.startswith('L1'):
        return 'L125x8' if '弦' in role else ('L45x4' if '次腹' in role else 'L75x5')
    if mid.startswith('L2'):
        return 'L125x8' if '弦' in role else ('L63x5' if '次腹' in role else 'L75x5')
    if mid.startswith('L3'):
        if '弦' in role: return 'L100x7'
        return 'L75x5' if 'W腹' in role else 'L63x5'
    if mid.startswith('LEG'):
        return 'L125x8' if z > 92364 else ('φ550x12' if z > 34254 else 'φ660x14')
    if mid.startswith('DIA'): return 'L63x5'
    if mid.startswith('VG'): return 'L160x10'
    if mid.startswith('XB'): return 'L63x5'
    if mid.startswith('BR'): return 'L160x10' if z < 50000 else 'L100x7'
    return 'L63x5'

def trim(p1, p2, z0):
    """保留线段 p1-p2 中 z >= z0 的上段; 全在下方返回 None"""
    if min(p1[2], p2[2]) >= z0 - 1: return p1, p2
    if max(p1[2], p2[2]) <= z0 + 1: return None
    lo, hi = (p1, p2) if p1[2] < p2[2] else (p2, p1)
    t = (z0 - lo[2]) / (hi[2] - lo[2])
    cut = [lo[k] + t*(hi[k]-lo[k]) for k in range(3)]
    cut[2] = z0
    return (cut, hi)

def build_variant(H, L):
    """H 呼高(挂点)m, L 接腿m -> members list (z 从地面向上)"""
    delta = V3_HANG - H*1000.0          # 塔z = v3z - delta
    z0 = delta + L*1000.0               # v3 坐标中的本体底截面
    members = []
    n = [0]
    def add(role, p1, p2, r, spec):
        n[0] += 1
        members.append({'mid': f'V{n[0]:04d}', 'role': role, 'spec': spec,
                        'r_mm': r,
                        'p1': [round(p1[0],1), round(p1[1],1), round(p1[2],1)],
                        'p2': [round(p2[0],1), round(p2[1],1), round(p2[2],1)]})
    rh = half_root(H, L)                # 地面半根开 (001根开表)

    # ---- 下延段 (H>99 且 z0<0: 本体比图面高, 合成 z_v3 in [z0,0]) ----
    if z0 < 0:
        wb0 = hw_v3(z0)                 # 延段底 = 接腿顶截面 (与接腿连续)
        NP = max(1, int(math.ceil(-z0/11000.0)))
        ph = -z0 / NP
        # 主材线: (z_v3=z0, x=wb0) -> (z_v3=0, x=13953)
        def xw(z):
            return wb0 + (13953.0-wb0)*(z - z0)/(-z0)
        for k in range(NP):
            a, b = z0 + k*ph, z0 + (k+1)*ph
            xa, xb = xw(a), xw(b)
            for sx in (1,-1):
                for sy in (1,-1):
                    add('本体主材(延)', (sx*xa, sy*xa, a-delta), (sx*xb, sy*xb, b-delta),
                        330.0, 'φ660x14')
            for face in range(4):
                # 注: lambda 内 xw(z) 用 v3 坐标, 返回 z 需平移到塔坐标 (z-delta)
                p = (lambda u,z: (u, xw(z), z-delta)) if face==0 else (lambda u,z: (u,-xw(z),z-delta)) \
                    if face==1 else (lambda u,z: (xw(z),u,z-delta)) if face==2 else (lambda u,z: (-xw(z),u,z-delta))
                add('延段斜材', p(-xa,a), p(xb,b), 60.0, 'L160x10')
                add('延段斜材', p(xa,a), p(-xb,b), 60.0, 'L160x10')
            for sx in (1,-1):
                add('延段横隔', (sx*xb,-xb,b-delta), (sx*xb,xb,b-delta), 60.0, 'L63x5')
                add('延段横隔', (-xb,sx*xb,b-delta), (xb,sx*xb,b-delta), 60.0, 'L63x5')

    # ---- 本体 (v3 裁剪+平移; 规格按 v3 原始位置, 段组合复用语义) ----
    for m in V3:
        z_orig = (m['p1'][2] + m['p2'][2]) / 2
        res = trim(m['p1'], m['p2'], z0)
        if res is None: continue
        p1, p2 = res
        p1 = [p1[0], p1[1], p1[2]-delta]; p2 = [p2[0], p2[1], p2[2]-delta]
        add(m['role'], p1, p2, m['r_mm'], spec_for(m['mid'], m['role'], z_orig))

    # ---- 接腿 (从地面半根开向本体底截面张开, 向外) ----
    if L > 0:
        wb = hw_v3(z0)                  # 本体底半宽 = 接腿顶截面
        r_leg = 330.0                   # φ660 半径
        def hwz(z): return rh + (wb - rh) * z / (L*1000.0)
        for sx in (1,-1):
            for sy in (1,-1):
                add('接腿主材', (sx*rh, sy*rh, 0.0), (sx*wb, sy*wb, L*1000), r_leg, 'φ660x14')
        NP = max(1, int(round(L / 1.5)))
        ph = L*1000.0 / NP
        for face in range(4):
            p = (lambda u,z: (u, hwz(z), z)) if face==0 else (lambda u,z: (u,-hwz(z),z)) \
                if face==1 else (lambda u,z: (hwz(z),u,z)) if face==2 else (lambda u,z: (-hwz(z),u,z))
            for k in range(NP+1):
                b = k*ph
                add('接腿横隔', p(-hwz(b),b), p(hwz(b),b), 60.0, 'L63x5')
        # 注: 001 图面接腿区仅有横隔(无大叉斜材), 故不建面内X撑
    return members

def to_scad(members, title):
    def sv(p): return f"[{p[0]:.0f}, {p[1]:.0f}, {p[2]:.0f}]"
    def col(role):
        return {'塔身主材':'ForestGreen','接腿主材':'SaddleBrown','X斜材':'DarkOrange',
                '菱形斜材':'DarkOrange','人字撑':'DarkOrange','接腿斜材':'SaddleBrown',
                '本体主材(延)':'ForestGreen','延段斜材':'DarkOrange',
                '横隔横材':'SteelBlue','接腿横隔':'SteelBlue','延段横隔':'SteelBlue'}.get(role,
                'Crimson' if role.startswith('L1') else 'MediumOrchid' if role.startswith('L2')
                else 'DeepPink' if role.startswith('L3') else 'Gray')
    out = [f'// {title}', '$fn=24;', '',
           'module tube(p1,p2,r,col){v=p2-p1;L=norm(v);ax=cross([0,0,1],v);translate(p1)color(col)if(norm(ax)<1e-9)rotate([0,v[2]>0?0:180,0])cylinder(h=L,r=r);else rotate(a=acos(min(1,max(-1,v[2]/L))),v=ax)cylinder(h=L,r=r);}', '']
    for m in members:
        p1, p2 = m.get('p1t', m['p1']), m.get('p2t', m['p2'])   # 下料坐标(留缝)
        out.append(f'tube([{p1[0]:.0f}, {p1[1]:.0f}, {p1[2]:.0f}],'
                   f'[{p2[0]:.0f}, {p2[1]:.0f}, {p2[2]:.0f}],{m["r_mm"]:.0f},"{col(m["role"])}");')
    return '\n'.join(out)

os.makedirs('demo/variants', exist_ok=True)

# ---- 002 本体及等长接腿重量合计表 (kg, 2026-09-30 高清裁剪读出) ----
# 重量仅依赖 d=135-H+L, 且按段组合分三族(90~96 / 99~117 / 120~135, 对应 P2/P3 变坡)
W002 = {
    90.0: [239479.2, 236455.3, 234082.8, 231486.5],   # L=0,1.5,3,4.5
    93.0: [246495.0, 242090.9, 239479.2, 236455.3],
    96.0: [252568.0, 250262.4, 246495.0, 242090.9],
    99.0: [269278.5, 264369.3, 261023.4, 259044.5],
    102.0: [274889.8, 272346.5, 269278.5, 264369.3],
    105.0: [282231.1, 277114.4, 274889.8, 272346.5],
    108.0: [291729.6, 286197.6, 283799.1, 280915.2],
    111.0: [297836.2, 294868.3, 291729.6, 286197.6],
    114.0: [304162.3, 300287.0, 297836.2, 294868.3],
    117.0: [310601.2, 307435.6, 304162.3, 300287.0],
    120.0: [343378.6, 337138.4, 332936.1, 330431.2],
    123.0: [349165.0, 346203.2, 343378.6, 337138.4],
    126.0: [357814.3, 353055.4, 349165.0, 346203.2],
    129.0: [364523.3, 361315.2, 357814.3, 353055.4],
    132.0: [380084.1, 374383.1, 370611.3, 367000.1],
    135.0: [389396.7, 383977.5, 380084.1, 374383.1],
}

summary = []
for i in range(16):
    H = 90.0 + 3.0*i
    for j, L in enumerate((0.0, 1.5, 3.0, 4.5)):
        members = apply_gaps(build_variant(H, L), GAP_MM)
        wt = 0.0
        for m in members:
            m['len_mm'] = m['cut_len_mm']      # 下料长(端头回退后), 重量按下料长
            uw = unit_w(m['spec'])
            m['wt_kg'] = round(uw*m['len_mm']/1000, 1) if uw else None
            if m['wt_kg']: wt += m['wt_kg']
        root = 2.0*half_root(H, L)          # 全根开 = 2x表值(001根开表,青色标注证实)
        height = H*1000.0 + TOP_SEG         # 塔全高 = 呼高(挂点) + 34708
        tag = f'SZK31102A_H{H:.0f}_L{L:.1f}'
        json.dump({'meta': {'tower': tag, 'hu_m': H, 'leg_m': L,
                            'root_mm': round(root), 'height_mm': round(height),
                            'members': len(members),
                            'gap_mm': GAP_MM,
                            'weight_kg': round(wt), 'weight002_kg': W002[H][j],
                            'spec_level': '粗略(无节点板/法兰)',
                            'note': '呼高=挂点高(呼称高); 根开=001根开表全根开(2x表值); '
                                    '本体=v3(99.0m呼高图面塔)截剪平移, H>99下延段为坡度合成; '
                                    '接腿区仅横隔(001图面证实); weight002=002合计表实测(含爬梯脚钉); '
                                    '杆件已拆件留缝(gap_mm, p1t/p2t为下料坐标)'},
                   'members': members},
                  open(f'demo/variants/{tag}.json', 'w', encoding='utf-8'), ensure_ascii=False)
        open(f'demo/variants/{tag}.scad', 'w', encoding='utf-8').write(
            to_scad(members, f'{tag}  呼高{H}m(挂点) 接腿{L}m 根开{root:.0f} 全高{height/1000:.1f}m '
                             f'杆件{len(members)} 模型约{wt/1000:.1f}t 002表约{W002[H][j]/1000:.0f}t'))
        summary.append((H, L, round(root), round(height), len(members), round(wt), W002[H][j]))

with open('demo/variants_summary.csv', 'w', encoding='utf-8-sig') as f:
    f.write('呼高m(挂点),接腿m,全根开mm,塔全高mm,杆件数,模型总重kg,002表重量kg\n')
    for H, L, root, h, n, wt, w2 in summary:
        f.write(f'{H},{L},{root},{h},{n},{wt},{w2}\n')

print(f'variants: {len(summary)} -> demo/variants/')
for H, L, root, h, n, wt, w2 in summary[:8] + summary[-4:]:
    print(f'H={H:5.1f} L={L:.1f} root={root:6.0f} height={h/1000:6.1f}m n={n:4d} '
          f'模型={wt/1000:6.1f}t 002={w2/1000:6.1f}t')
