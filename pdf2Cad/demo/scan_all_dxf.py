# -*- coding: utf-8 -*-
"""批量扫描所有 DXF：实体统计/图层/文字/坐标范围 → catalog_db.json"""
import sys, os, glob, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from collections import Counter
import ezdxf

DXF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       '图纸', 'dxf和dwg')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'demo', 'catalog_db.json')

files = sorted(glob.glob(os.path.join(DXF_DIR, '*.dxf')))
print(f'total dxf: {len(files)}', flush=True)

catalog = []
for idx, f in enumerate(files):
    base = os.path.basename(f)
    m = re.search(r'(\d+)\.dxf$', base)
    num = int(m.group(1)) if m else 0
    try:
        doc = ezdxf.readfile(f)
        msp = doc.modelspace()
        tc = Counter(e.dxftype() for e in msp)
        lc = Counter(e.dxf.layer for e in msp)

        # text
        texts = []
        for e in msp:
            t = e.dxftype()
            if t == 'TEXT':
                texts.append(e.dxf.text)
            elif t == 'MTEXT':
                texts.append(e.plain_text())

        # coord range
        xs, ys = [], []
        for e in msp:
            t = e.dxftype()
            if t == 'LINE':
                xs += [e.dxf.start.x, e.dxf.end.x]
                ys += [e.dxf.start.y, e.dxf.end.y]
            elif t == 'LWPOLYLINE':
                for p in e.get_points('xy'):
                    xs.append(p[0]); ys.append(p[1])
        coord = f'{min(xs):.0f},{min(ys):.0f} to {max(xs):.0f},{max(ys):.0f}' if xs else ''

        # clean geometry count
        clean = sum(1 for e in msp if e.dxftype() in ('LINE','LWPOLYLINE','CIRCLE','ARC'))

        catalog.append({
            'num': num,
            'file': base,
            'size_mb': round(os.path.getsize(f)/1e6, 1),
            'entity_types': dict(tc.most_common(10)),
            'total_entities': sum(tc.values()),
            'clean_geo': clean,
            'hatch': tc.get('HATCH', 0),
            'text_count': len(texts),
            'text_samples': texts[:5],
            'layers': dict(lc.most_common(5)),
            'coord_range': coord,
        })
    except Exception as e:
        catalog.append({'num': num, 'file': base, 'error': str(e)[:100]})

    if idx % 20 == 0:
        print(f'  {idx}/{len(files)}: {num}', flush=True)

json.dump(catalog, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'saved {OUT} ({len(catalog)} sheets)', flush=True)
