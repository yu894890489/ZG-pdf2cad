# -*- coding: utf-8 -*-
"""probe Print2CAD-converted DXF: entity types / layers / text / coord range / polyline vertex dist"""
import sys, os, glob, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from collections import Counter
try:
    import ezdxf
except ImportError:
    os.system('pip install ezdxf -q')
    import ezdxf

DXF_DIR = r'F:\workspace\orca\brainStorm\pdf2Cad\图纸\dxf和dwg'
files = sorted(glob.glob(os.path.join(DXF_DIR, '*.dxf')))
print(f'dxf files: {len(files)}')

targets = [f for f in files
           if re.search(r'page-1\.dxf$|page-10\.dxf$|page-100\.dxf$', os.path.basename(f).lower())]
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
    print('  entity types(top15):', dict(tc.most_common(15)))
    lc = Counter(e.dxf.layer for e in msp)
    print('  layers(top12):', dict(lc.most_common(12)))

    texts = []
    for e in msp:
        if e.dxftype() == 'TEXT':
            texts.append(e.dxf.text)
        elif e.dxftype() == 'MTEXT':
            texts.append(e.plain_text())
    print(f'  TEXT/MTEXT count: {len(texts)}')
    for t in texts[:20]:
        print('    text:', repr(t[:70]))

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
        print(f'  coord range: x [{min(xs):.1f}, {max(xs):.1f}]  y [{min(ys):.1f}, {max(ys):.1f}]')

    vc = Counter()
    for e in msp:
        if e.dxftype() == 'LWPOLYLINE':
            n = len(e.get_points('xy'))
            key = '1-4' if n <= 4 else ('5-20' if n <= 20 else '>20')
            vc[key] += 1
    print('  LWPOLYLINE vertex dist:', dict(vc))

    lens = []
    for e in msp:
        if e.dxftype() == 'LINE':
            lens.append(e.dxf.start.distance(e.dxf.end))
    if lens:
        lens.sort()
        n = len(lens)
        print(f'  LINE len: n={n} median={lens[n//2]:.1f} p90={lens[int(n*0.9)]:.1f} max={lens[-1]:.1f}')
