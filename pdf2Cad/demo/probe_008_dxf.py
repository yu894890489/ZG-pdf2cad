# -*- coding: utf-8 -*-
"""探查 008 下平面 DXF（Print2CAD 转出）：HATCH 过滤后的几何质量 + 长弦线是否存在"""
import sys, os, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from collections import Counter
try:
    import ezdxf
except ImportError:
    os.system('pip install ezdxf -q')
    import ezdxf

DXF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       '图纸', 'dxf和dwg')
files = sorted(glob.glob(os.path.join(DXF_DIR, '*.dxf')))
print(f'dxf total: {len(files)}')

# 008 下平面 = Page-8；同时取 Page-1(001总图) 对照
targets = [f for f in files
           if os.path.basename(f).lower().endswith(('page-8.dxf', 'page-1.dxf'))]
print('targets:', [os.path.basename(t) for t in targets])

for f in targets:
    print('=' * 70)
    print(os.path.basename(f), f'{os.path.getsize(f)/1e6:.1f} MB')
    try:
        doc = ezdxf.readfile(f)
    except Exception as e:
        print('  read error:', repr(e)[:120])
        continue
    msp = doc.modelspace()

    tc = Counter(e.dxftype() for e in msp)
    print('  entity types:', dict(tc.most_common(12)))

    # 过滤 HATCH 后的"干净几何"
    geo = [e for e in msp if e.dxftype() in ('LINE', 'LWPOLYLINE', 'CIRCLE', 'ARC')]
    print(f'  clean geometry (non-HATCH): {len(geo)}')

    # LINE 长度分布（找长弦线）
    lens = []
    for e in geo:
        if e.dxftype() == 'LINE':
            lens.append((e.dxf.start.distance(e.dxf.end), e))
        elif e.dxftype() == 'LWPOLYLINE':
            pts = e.get_points('xy')
            d = sum(math.dist(pts[i][:2], pts[i+1][:2]) for i in range(len(pts)-1))
            lens.append((d, e))
    lens.sort(key=lambda t: -t[0])
    print(f'  geometry len: n={len(lens)}')
    if lens:
        print('  top10 longest (len, type, layer):')
        for d, e in lens[:10]:
            print(f'    {d:8.1f}  {e.dxftype():12s}  layer={e.dxf.layer}')

    # 文字
    texts = sum(1 for e in msp if e.dxftype() in ('TEXT', 'MTEXT'))
    print(f'  TEXT/MTEXT: {texts}')

    # 坐标范围
    xs, ys = [], []
    for e in geo:
        if e.dxftype() == 'LINE':
            xs += [e.dxf.start.x, e.dxf.end.x]
            ys += [e.dxf.start.y, e.dxf.end.y]
        elif e.dxftype() == 'LWPOLYLINE':
            for p in e.get_points('xy'):
                xs.append(p[0]); ys.append(p[1])
    if xs:
        print(f'  coord range: x [{min(xs):.1f}, {max(xs):.1f}]  y [{min(ys):.1f}, {max(ys):.1f}]')
