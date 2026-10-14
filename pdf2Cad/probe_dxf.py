# -*- coding: utf-8 -*-
"""探查 Print2CAD 转换出的 DXF：实体类型/图层/文字/坐标范围/顶点分布"""
import os, sys, glob
from collections import Counter
import ezdxf

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DXF_DIR = r'F:\workspace\orca\brainStorm\pdf2Cad\图纸\dxf和dwg'
files = sorted(glob.glob(os.path.join(DXF_DIR, '*.dxf')))
print(f'dxf files: {len(files)}')

# 目标: Page-1(001总图), Page-10(010下导线横担), Page-100(100身部段)
targets = [f for f in files
           if os.path.basename(f).lower().endswith(('page-1.dxf', 'page-10.dxf', 'page-100.dxf'))]

for f in targets:
    name = os.path.basename(f)
    print('=' * 70)
    print(f'{name}  {os.path.getsize(f)/1e6:.1f} MB')
    try:
        doc = ezdxf.readfile(f)
    except Exception as e:
        print('  read error:', repr(e)[:100])
        continue
    msp = doc.modelspace()

    # 1) 实体类型
    tc = Counter(e.dxftype() for e in msp)
    print('entity types:', dict(tc.most_common(15)))

    # 2) 图层分布
    lc = Counter(e.dxf.layer for e in msp)
    print('layers(top12):', dict(lc.most_common(12)))

    # 3) 文字实体（判断文字是真文字还是转曲轮廓）
    texts = []
    for e in msp:
        if e.dxftype() == 'TEXT':
            texts.append(e.dxf.text)
        elif e.dxftype() == 'MTEXT':
            texts.append(e.plain_text())
    print(f'TEXT/MTEXT count: {len(texts)}')
    for t in texts[:20]:
        print('  text:', repr(t[:70]))

    # 4) 坐标范围
    xs, ys = [], []
    for e in msp:
        t = e.dxftype()
        if t == 'LINE':
            xs += [e.dxf.start.x, e.dxf.end.x]
            ys += [e.dxf.start.y, e.dxf.end.y]
        elif t == 'LWPOLYLINE':
            for p in e.get_points():
                xs.append(p[0]); ys.append(p[1])
    if xs:
        print(f'coord range: x [{min(xs):.1f}, {max(xs):.1f}]  y [{min(ys):.1f}, {max(ys):.1f}]')

    # 5) LWPOLYLINE 顶点数分布（判断是否字形碎线）
    vc = Counter()
    for e in msp:
        if e.dxftype() == 'LWPOLYLINE':
            n = len(e.get_points())
            key = '1-4' if n <= 4 else ('5-20' if n <= 20 else '>20')
            vc[key] += 1
    print('LWPOLYLINE vertex dist:', dict(vc))
