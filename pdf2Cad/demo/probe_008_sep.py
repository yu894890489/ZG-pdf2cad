# -*- coding: utf-8 -*-
"""008 下平面：找两片桁架弦杆的 y 间距（SC=30）"""
import sys, json, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

axes = json.load(open('demo/dxf008_axes.json', encoding='utf-8'))['axes']
SC = 30.0
# 只看长轴线，按角度分组
long_ax = [a for a in axes if a['ext'] > 100]
print(f'long axes (>100 page-mm): {len(long_ax)}')
for a in long_ax:
    dx, dy = a['b'][0]-a['a'][0], a['b'][1]-a['a'][1]
    ang = math.degrees(math.atan2(dy, dx)) % 180
    print(f"  ({a['a'][0]:>7.1f},{a['a'][1]:>7.1f}) -> ({a['b'][0]:>7.1f},{a['b'][1]:>7.1f}) ext={a['ext']:>6.0f} ang={ang:6.1f} n={a['nseg']}")
