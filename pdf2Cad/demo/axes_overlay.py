# -*- coding: utf-8 -*-
"""Overlay detected axis clusters on the detail view for verification."""
import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw

data = json.load(open('demo/data.json', encoding='utf-8'))
clusters = json.load(open('demo/axes.json', encoding='utf-8'))

RX0, RY0, RX1, RY1 = 850, 500, 2100, 1330
S = 1.2
img = Image.new('RGB', (int((RX1-RX0)*S), int((RY1-RY0)*S)), 'white')
d = ImageDraw.Draw(img)

def T(p): return ((p[0]-RX0)*S, (p[1]-RY0)*S)

for ln in data['lines']:
    a, b = ln['a'], ln['b']
    if RX0 <= min(a[0], b[0]) and max(a[0], b[0]) <= RX1 and RY0 <= min(a[1], b[1]) and max(a[1], b[1]) <= RY1:
        d.line([T(a), T(b)], fill=(190, 205, 235), width=1)

colors = {'V': (220, 30, 30), 'H': (0, 150, 60), 'D': (240, 130, 0)}
for i, c in enumerate(clusters):
    col = colors.get(c['kind'], (150, 0, 200))
    d.line([T(c['a']), T(c['b'])], fill=col, width=3)
    m = ((c['a'][0]+c['b'][0])/2, (c['a'][1]+c['b'][1])/2)
    d.text((m[0]-RX0)*S and T(m), str(i), fill=(80, 0, 200))

img.save('demo/axes_overlay.png')
print('saved demo/axes_overlay.png', img.size)
