# -*- coding: utf-8 -*-
"""以 001 为权威基准全塔重建
塔身: 直线锥腿(±13953,0 → ±2904,92364) + 头部收口 + 菱形/X 腹杆
横担: L1 地线支架 W 形 (z 130880~133860)
      L2/L3 芬克式悬臂桁架 (下弦水平 + 上弦斜 + W 折线腹杆)
所有坐标来自 001 正视图轴线提取 (SC=37.17mm/pt)
"""
import sys, os, json, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OUT = 'demo/frame.json'

members = []
_n = [0]
def add(role, p1, p2, r, spec='参数化', mid_prefix='M'):
    _n[0] += 1
    members.append({'mid': f'{mid_prefix}{_n[0]:04d}', 'role': role, 'spec': spec,
                    'r_mm': r, 'p1': [round(p1[0],1), round(p1[1],1), round(p1[2],1)],
                    'p2': [round(p2[0],1), round(p2[1],1), round(p2[2],1)]})

def hw(z):
    """塔身面半宽 (front view silhouette)"""
    if z <= 92364:
        return 13953.0 + (2904.0-13953.0) * z/92364.0
    pts = [(92364,2904),(96462,2791),(122610,1980),(128199,1808),(133860,1637)]
    for (z0,w0),(z1,w1) in zip(pts, pts[1:]):
        if z0 <= z <= z1:
            return w0 + (w1-w0)*(z-z0)/(z1-z0)
    return 1637.0

# ================= 1. 塔身 =================
LEG_PTS = [(0.0,13953.0),(92364.0,2904.0),(96462.0,2791.0),
           (122610.0,1980.0),(128199.0,1808.0),(133860.0,1637.0)]
# 4 根角柱
for sx in (1,-1):
    for sy in (1,-1):
        for (z0,w0),(z1,w1) in zip(LEG_PTS, LEG_PTS[1:]):
            add('塔身主材', (sx*w0, sy*w0, z0), (sx*w1, sy*w1, z1), 160.0, '主材', 'LEG')

# 横隔面 (图纸有水平横材的标高)
DIA_Z = [2782.0, 19355.0, 34254.0, 48409.0, 60330.0, 71132.0, 92364.0, 104434.0, 133860.0]
for z in DIA_Z:
    w = hw(z)
    corners = [(sx*w, sy*w, z) for sx in (1,-1) for sy in (1,-1)]
    edges = [(0,1),(0,2),(1,3),(2,3)]
    for i,j in edges:
        add('横隔横材', corners[i], corners[j], 55.0, '横隔', 'DIA')

# 菱形腹杆面板 (front view: (0,z0)->(±hw_mid,z_mid)->(0,z1))
DIA_PANELS = [(19355.0,34254.0),(34254.0,48409.0),(48409.0,60330.0),
              (60330.0,71132.0),(71132.0,81934.0),(81934.0,92364.0)]
for z0, z1 in DIA_PANELS:
    zm = (z0+z1)/2.0
    wm = hw(zm)
    for face in range(4):
        # face 0/1: y=±hw 面 (x 为面内横坐标); face 2/3: x=±hw 面 (y 为面内横坐标)
        for sgn in (1,-1):
            if face == 0:   p = lambda u, z: (u,  hw(z), z)
            elif face == 1: p = lambda u, z: (u, -hw(z), z)
            elif face == 2: p = lambda u, z: ( hw(z), u, z)
            else:           p = lambda u, z: (-hw(z), u, z)
            add('菱形斜材', p(0.0, z0), p(sgn*wm, zm), 60.0, '斜材', 'BR')
            add('菱形斜材', p(sgn*wm, zm), p(0.0, z1), 60.0, '斜材', 'BR')

# X 腹杆面板 (角到角全宽交叉)
X_PANELS = [(92364.0,96461.0),(96461.0,100558.0),(100558.0,104434.0),
            (104434.0,108232.0),(108232.0,112032.0),(112032.0,115832.0),
            (115832.0,119630.0),(119630.0,122610.0),(122610.0,125442.0),
            (125442.0,128199.0),(128199.0,130880.0),(130880.0,133860.0)]
for z0, z1 in X_PANELS:
    w0, w1 = hw(z0), hw(z1)
    for face in range(4):
        if face == 0:   p = lambda u, z: (u,  hw(z), z)
        elif face == 1: p = lambda u, z: (u, -hw(z), z)
        elif face == 2: p = lambda u, z: ( hw(z), u, z)
        else:           p = lambda u, z: (-hw(z), u, z)
        add('X斜材', p(-w0, z0), p(w1, z1), 60.0, '斜材', 'XB')
        add('X斜材', p(w0, z0), p(-w1, z1), 60.0, '斜材', 'XB')

# 底部人字撑 (脚部两点 -> 面中心顶)
for face in range(4):
    if face == 0:   p = lambda u, z: (u,  hw(z), z)
    elif face == 1: p = lambda u, z: (u, -hw(z), z)
    elif face == 2: p = lambda u, z: ( hw(z), u, z)
    else:           p = lambda u, z: (-hw(z), u, z)
    add('人字撑', p(-13953.0, 0.0), p(0.0, 19355.0), 80.0, '斜材', 'VG')
    add('人字撑', p(13953.0, 0.0), p(0.0, 19355.0), 80.0, '斜材', 'VG')

# ================= 2. 横担 =================
# 每层: (chord_top, chord_bot, webs自动W连接, sub_brace, y半宽root/tip)
# 坐标均取自 001 正视图轴线
def build_crossarm(tag, zref, top_pts, bot_pts, sub, half_root, half_tip, r_chord, r_web):
    """一侧横担 (sx=±1 镜像). top_pts/bot_pts: [x, z] 列表 (x 从塔面向外).
       sub: [(x1,z1),(x2,z2),(xh1,zh),(xh2,zh)] 次腹杆: 斜杆两根 + 横杆"""
    reach = bot_pts[-1][0] - bot_pts[0][0]
    x_root = bot_pts[0][0]
    def yh(x):
        t = max(0.0, min(1.0, (x - x_root)/reach))
        return half_root + (half_tip-half_root)*t
    for sx in (1,-1):
        X = lambda v: sx*v
        for sy in (1,-1):
            Y = lambda v: sy*v
            # 弦杆 (分段折线, 随 y 收窄)
            for pts, role, rc in ((top_pts, f'{tag}上弦', r_chord), (bot_pts, f'{tag}下弦', r_chord)):
                for (x0,z0),(x1,z1) in zip(pts, pts[1:]):
                    add(role, (X(x0),Y(yh(x0)),z0), (X(x1),Y(yh(x1)),z1), rc, '横担主材', tag)
            # W 折线腹杆: bot[0]->top[1]->bot[1]->top[2]->... 交替
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
            # 次腹杆 (节间 1 内小三角)
            if sub:
                (xs1, zs1), (xs2, zs2), (xh1, zh), (xh2, zh2) = sub
                add(f'{tag}次腹杆', (X(xs1),Y(yh(xs1)),zs1), (X(xh1),Y(yh(xh1)),zh), 45.0, '斜材', tag)
                add(f'{tag}次腹杆', (X(xs1),Y(yh(xs1)),zs1), (X(xh2),Y(yh(xh2)),zh), 45.0, '斜材', tag)
                add(f'{tag}次腹杆', (X(xh1),Y(yh(xh1)),zh), (X(xh2),Y(yh(xh2)),zh), 45.0, '横材', tag)
            # 横隔竖杆/横杆 (前后片连接)
            for pts in (top_pts, bot_pts):
                for (x, z) in pts[1:-1]:
                    add(f'{tag}横隔', (X(x),-Y(yh(x)),z), (X(x),Y(yh(x)),z), 45.0, '横隔', tag)
        # 端部封口: 上弦末端 -> 下弦末端
        xt, zt = top_pts[-1]; xb, zb = bot_pts[-1]
        for sy in (1,-1):
            add(f'{tag}端斜杆', (X(xt),sy*yh(xt),zt), (X(xb),sy*yh(xb),zb), 60.0, '横担主材', tag)
        add(f'{tag}端横梁', (X(xb),-yh(xb),zb), (X(xb),yh(xb),zb), 60.0, '横隔', tag)

# ---- L1 地线支架 (W形上弦: 塔顶缓降->谷点11405->上翘峰/挂线点16021, 001 DXF 精确提取 2026-09-30) ----
# 004单线图(1:100标注实为1:134, 15300/21500/23000 x0.745 = 11405/16021/17140)
L1_top = [(1700,133860),(4245,133484),(6853,133107),(9125,132779),(11405,132498)]
L1_bot = [(1700,130880),(5780,130880),(7806,130880),(9831,130880),(11405,130880)]
L1_sub = [(3753,130880),(3753,130880),(2987,132191),(5011,132191)]
build_crossarm('L1', 130880, L1_top, L1_bot, L1_sub, 1500.0, 700.0, 90.0, 55.0)

# W头(挂线架): 谷点11405 -> 峰16021(高出塔顶1.1m), 下弦延伸上翘, 头内W腹杆+133838水平杆, 尾杆到17140
for sx in (1,-1):
    X = lambda v: sx*v
    def yh2(x):  # 头部 y 半宽 700->600 线性
        t = (abs(x)-11405)/(17140-11405)
        return 700.0 - 100.0*t
    hw = [((11405,132498),(16021,134955)),          # 头上弦
          ((11405,130880),(16021,133838)),          # 头下弦
          ((16021,133838),(16021,134955)),          # 端竖杆
          ((13922,133838),(17140,133838))]          # 水平杆+挂线尾
    for (a,b) in hw:
        for sy in (1,-1):
            add('L1头弦', (X(a[0]),sy*yh2(a[0]),a[1]), (X(b[0]),sy*yh2(b[0]),b[1]), 60.0, '横担主材', 'L1')
    zig = [(11405,132498),(12451,131535),(12665,133167),(13497,132209),
           (13922,133838),(14759,133024),(16021,134955)]   # 头内 W 折线腹杆(001节点提取)
    for (a,b) in zip(zig, zig[1:]):
        for sy in (1,-1):
            add('L1头腹杆', (X(a[0]),sy*yh2(a[0]),a[1]), (X(b[0]),sy*yh2(b[0]),b[1]), 45.0, '斜材', 'L1')

# ---- L2 中导线横担 (芬克式, 下弦 115832) ----
L2_top = [(2072,119630),(4690,118613),(7308,117597),(9928,116578)]
L2_bot = [(2186,115832),(6405,115832),(8490,115832),(10278,115832)]
L2_sub = [(4296,115832),(4296,115832),(3439,117221),(5546,117221)]
build_crossarm('L2', 115832, L2_top, L2_bot, L2_sub, 1850.0, 520.0, 90.0, 55.0)

# ---- L3 下导线横担 (芬克式, 下弦 100558) ----
L3_top = [(2534,104434),(5181,103390),(7828,102347),(10475,101303)]
L3_bot = [(2658,100558),(6777,100558),(8789,100558),(10799,100558)]
L3_sub = [(4714,100558),(4714,100558),(3916,101974),(5979,101974)]
build_crossarm('L3', 100558, L3_top, L3_bot, L3_sub, 2000.0, 550.0, 90.0, 55.0)

# ================= 输出 =================
frame = {'meta': {
            'tower': 'SZK31102A', 'height_mm': 135000,
            'root_half_mm': 13953.0, 'note': '001 正视图重建 v3: 菱形/X 腹杆 + W形地线支架 + 芬克式横担'},
         'members': members}
json.dump(frame, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
from collections import Counter
print(f'members: {len(members)}')
print(Counter(m['role'] for m in members).most_common(20))

# ================= SCAD =================
def sv(p): return f"[{p[0]:.0f}, {p[1]:.0f}, {p[2]:.0f}]"
def col(role, mid):
    if mid.startswith('LEG'): return 'ForestGreen'
    if mid.startswith(('BR','VG')): return 'DarkOrange'
    if mid.startswith('XB'): return 'DarkOrange'
    if mid.startswith('DIA'): return 'SteelBlue'
    if mid.startswith('L1'): return 'Crimson'
    if mid.startswith('L2'): return 'MediumOrchid'
    if mid.startswith('L3'): return 'DeepPink'
    return 'Gray'
out = ['// SZK31102A 135m — 全塔 v3 (001基准重建: 塔身菱形/X腹杆 + W形地线支架 + 芬克式横担)',
       '// 1:1mm; 根开27906; 总高135000', '$fn=24;', '',
       'module tube(p1,p2,r,col){v=p2-p1;L=norm(v);ax=cross([0,0,1],v);translate(p1)color(col)if(norm(ax)<1e-9)rotate([0,v[2]>0?0:180,0])cylinder(h=L,r=r);else rotate(a=acos(min(1,max(-1,v[2]/L))),v=ax)cylinder(h=L,r=r);}', '']
for m in members:
    out.append(f'tube({sv(m["p1"])},{sv(m["p2"])},{m["r_mm"]:.0f},"{col(m["role"], m["mid"])}");')
scad_path = 'demo/tower_frame.scad'
open(scad_path, 'w', encoding='utf-8').write('\n'.join(out))
import shutil
shutil.copy(scad_path, 'tower_frame.scad')
print('scad saved -> demo/tower_frame.scad + tower_frame.scad')

# ================= 正视图对比 =================
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
d1 = json.load(open('demo/data001.json', encoding='utf-8'))
CX, Y_BOT, SC = 624.0, 3749.0, 135000.0/3632.0
fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 16), sharey=True)
for ln in d1['lines']:
    (xa, ya), (xb, yb) = ln['a'], ln['b']
    mx = (xa+xb)/2
    if not (100 <= mx <= 1150): continue
    a1.plot([(xa-CX)*SC, (xb-CX)*SC], [(Y_BOT-ya)*SC, (Y_BOT-yb)*SC], color='black', lw=0.3)
a1.set_title('001 drawing'); a1.set_xlim(-16500, 16500); a1.set_ylim(-2000, 137000); a1.set_aspect('equal')
for m in members:
    p1, p2, mid = m['p1'], m['p2'], m['mid']
    c = 'gray'
    if mid.startswith('LEG'): c = 'green'
    elif mid.startswith(('BR','XB','VG')): c = 'darkorange'
    elif mid.startswith('DIA'): c = 'steelblue'
    elif mid.startswith('L1'): c = 'crimson'
    elif mid.startswith('L2'): c = 'mediumorchid'
    elif mid.startswith('L3'): c = 'deeppink'
    a2.plot([p1[0],p2[0]],[p1[2],p2[2]], color=c, lw=0.6)
a2.set_title('rebuild v3'); a2.set_xlim(-16500, 16500); a2.set_ylim(-2000, 137000); a2.set_aspect('equal')
plt.tight_layout(); plt.savefig('demo/compare_v3.png', dpi=85)
print('saved demo/compare_v3.png')
