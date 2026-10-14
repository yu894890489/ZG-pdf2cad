# -*- coding: utf-8 -*-
"""Visualize 001 lines to locate the tower elevation region."""
import json, sys
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw

data = json.load(open('demo/data001.json', encoding='utf-8'))
W, H = data['page']
S = 0.28
img = Image.new('RGB', (int(W * S), int(H * S)), 'white')
d = ImageDraw.Draw(img)
def T(p): return (p[0] * S, p[1] * S)
for ln in data['lines']:
    a, b = ln['a'], ln['b']
    L = ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5
    col = (150, 170, 220) if L < 200 else ((30, 90, 200) if L < 600 else (200, 30, 30))
    d.line([T(a), T(b)], fill=col, width=1)
img.save('demo/p001_lines.png')
print('saved demo/p001_lines.png', img.size)
