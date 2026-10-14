# -*- coding: utf-8 -*-
"""Step 1b: overlay classification result on rendered page for visual verification."""
import json, sys
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw

data = json.load(open('demo/data.json', encoding='utf-8'))
W, H = data['page']
SCALE = 0.5  # 1 pt -> 0.5 px
img = Image.new('RGB', (int(W*SCALE), int(H*SCALE)), 'white')
d = ImageDraw.Draw(img)

def sx(p): return (p[0]*SCALE, p[1]*SCALE)

for ln in data['lines']:
    d.line([sx(ln['a']), sx(ln['b'])], fill=(160,190,255), width=1)
for c in data['circles']:
    x, y = c['c']; r = c['r']
    d.ellipse([sx((x-r,y-r)), sx((x+r,y+r))], outline=(0,160,0), width=1)
for a in data['arcs']:
    pts = [sx(p) for cv in a['curves'] for p in cv]
    if len(pts) > 1:
        d.line(pts, fill=(255,140,0), width=1)
for g in data['glyphs']:
    x0, y0, x1, y1 = [v*SCALE for v in g['bbox']]
    d.rectangle([x0, y0, x1, y1], outline=(255,0,0), width=1)

img.save('demo/overlay.png')
print('saved demo/overlay.png', img.size)
