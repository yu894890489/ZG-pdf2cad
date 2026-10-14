# -*- coding: utf-8 -*-
"""探查 AutoCAD 2025 PDFIMPORT 转出的 DXF（008 中导线横担）"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from collections import Counter
import ezdxf

f = os.path.join('图纸', 'dxf和dwg', '37-SA36901S-T0121-008.dxf')
print(f'{f}  {os.path.getsize(f)/1e6:.1f} MB')
doc = ezdxf.readfile(f)
msp = doc.modelspace()

tc = Counter(e.dxftype() for e in msp)
print('entity types(top15):', dict(tc.most_common(15)))

lc = Counter(e.dxf.layer for e in msp)
print('layers(top12):', dict(lc.most_common(12)))

# 文字
texts = []
for e in msp:
    t = e.dxftype()
    if t == 'TEXT':
        texts.append(e.dxf.text)
    elif t == 'MTEXT':
        texts.append(e.plain_text())
print(f'TEXT/MTEXT: {len(texts)}')
for t in texts[:25]:
    print('  text:', repr(t[:70]))

# 坐标范围
xs, ys = [], []
for e in msp:
    t = e.dxftype()
    if t == 'LINE':
        xs += [e.dxf.start.x, e.dxf.end.x]
        ys += [e.dxf.start.y, e.dxf.end.y]
    elif t == 'LWPOLYLINE':
        for p in e.get_points('xy'):
            xs.append(p[0]); ys.append(p[1])
if xs:
    print(f'coord range: x [{min(xs):.1f}, {max(xs):.1f}]  y [{min(ys):.1f}, {max(ys):.1f}]')

# LWPOLYLINE 顶点数分布
vc = Counter()
for e in msp:
    if e.dxftype() == 'LWPOLYLINE':
        n = len(e.get_points('xy'))
        vc['1-4' if n <= 4 else ('5-20' if n <= 20 else '>20')] += 1
print('LWPOLYLINE vertex dist:', dict(vc))

# LINE 长度分布
lens = []
for e in msp:
    if e.dxftype() == 'LINE':
        lens.append(e.dxf.start.distance(e.dxf.end))
if lens:
    lens.sort()
    n = len(lens)
    print(f'LINE len: n={n} median={lens[n//2]:.1f} p90={lens[int(n*0.9)]:.1f} max={lens[-1]:.1f}')
