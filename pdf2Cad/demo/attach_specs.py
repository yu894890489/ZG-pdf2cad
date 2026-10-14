# -*- coding: utf-8 -*-
"""规格挂接 v3.1: 将 OCR 明细表得到的规格按 部位+标高 挂到 frame.json 各杆件
来源:
  004 地线支架明细表: 弦杆L125x8 次弦L110x7 斜材L90x7/L75x5 次腹L45x4
  005/006 上导线横担:  弦杆L125x8 腹杆L63x5 挂点加强L220x24
  007/008 中导线横担:  弦杆L100x7 腹杆L75x6/L63x5
  013 身部上段:        主材L125x8 斜材L63x5
  110 腿部段:          主材钢管 φ660x14 Q420
  中段无OCR数据 -> 插值估算(标注'估')
所有规格均为粗略级(001系图纸明细表精度有限)
"""
import sys, json, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

frame = json.load(open('demo/frame.json', encoding='utf-8'))
ms = frame['members']

# ---- 截面特性表 (mm, kg/m) ----
ANGLE = {  # 角钢: (A_cm2, kg/m)
    'L45x4': (3.49, 2.74), 'L63x5': (6.14, 4.82), 'L75x3': (4.43, 3.48),
    'L75x5': (7.41, 5.82), 'L75x6': (8.79, 6.91), 'L80x6': (9.28, 7.28),
    'L80x7': (10.71, 8.41), 'L90x6': (10.48, 8.23), 'L90x7': (12.11, 9.51),
    'L100x7': (13.80, 10.83), 'L110x7': (15.20, 11.93), 'L125x8': (19.75, 15.50),
    'L125x12': (28.71, 22.54), 'L140x10': (26.73, 20.98), 'L160x10': (31.00, 24.34),
    'L180x12': (41.99, 32.96), 'L200x14': (54.60, 42.86), 'L220x24': (100.4, 78.8),
}
TUBE = {  # 钢管 外径x壁厚: (kg/m)
    'φ480x10': (115.06), 'φ530x12': (153.03), 'φ550x12': (159.57),
    'φ660x14': (223.39),
}

def unit_w(spec):
    if spec in ANGLE: return ANGLE[spec][1]
    if spec in TUBE: return TUBE[spec]
    return None

def spec_for(m):
    """返回 (规格, 标注)"""
    mid, role = m['mid'], m['role']
    z = (m['p1'][2] + m['p2'][2]) / 2
    if mid.startswith('L1'):
        if '弦' in role: return 'L125x8', '004实测'
        if '次腹' in role: return 'L45x4', '004实测'
        return 'L75x5', '004实测'
    if mid.startswith('L2'):
        if '弦' in role: return 'L125x8', '005实测'
        return 'L63x5', '005实测'
    if mid.startswith('L3'):
        if '弦' in role: return 'L100x7', '007/008实测'
        if 'W腹' in role: return 'L75x5', '008实测'
        return 'L63x5', '008实测'
    if mid.startswith('LEG'):
        if z > 92364: return 'L125x8', '013实测'
        if z > 34254: return 'φ550x12', '估(插值)'
        return 'φ660x14', '110实测'
    if mid.startswith('DIA'): return 'L63x5', '同族推算'
    if mid.startswith('VG'): return 'L160x10', '估'
    if mid.startswith('XB'): return 'L63x5', '013实测(斜材)'
    if mid.startswith('BR'):
        return ('L160x10', '估') if z < 50000 else ('L100x7', '估')
    return '参数化', ''

n_att = 0
for m in ms:
    spec, note = spec_for(m)
    m['spec'] = spec
    m['spec_note'] = note
    m['len_mm'] = round(math.dist(m['p1'], m['p2']), 1)
    uw = unit_w(spec)
    m['unit_kg'] = uw
    m['wt_kg'] = round(uw * m['len_mm'] / 1000, 1) if uw else None
    if uw: n_att += 1

frame['meta']['spec_level'] = '粗略: 规格来自 004/005/007/008/010/013/110 明细表OCR, 中段为插值估算'
json.dump(frame, open('demo/frame.json', 'w', encoding='utf-8'), ensure_ascii=False)

# ---- BOM 汇总 ----
from collections import defaultdict
groups = defaultdict(lambda: {'n': 0, 'len': 0.0, 'wt': 0.0})
for m in ms:
    k = (m['spec'], m['spec_note'])
    g = groups[k]
    g['n'] += 1
    g['len'] += m['len_mm']
    if m['wt_kg']: g['wt'] += m['wt_kg']

rows = sorted(groups.items(), key=lambda kv: -(kv[1]['wt'] or 0))
with open('demo/bom.csv', 'w', encoding='utf-8-sig') as f:
    f.write('规格,来源,数量,总长m,总重kg\n')
    for (spec, note), g in rows:
        f.write(f'{spec},{note},{g["n"]},{g["len"]/1000:.1f},{g["wt"]:.1f}\n')

total_w = sum(g['wt'] for _, g in rows)
print(f'members: {len(ms)}, 挂接重量: {n_att}, 总重: {total_w/1000:.2f} t (图纸全塔约 {sum([12957.3,571.8]) if False else "?"} t)')
print(f'{"规格":<12} {"来源":<14} {"数量":>4} {"总长m":>8} {"总重kg":>9}')
for (spec, note), g in rows:
    print(f'{spec:<12} {note:<14} {g["n"]:>4} {g["len"]/1000:>8.1f} {g["wt"]:>9.1f}')
print('saved demo/bom.csv')
