# -*- coding: utf-8 -*-
"""规格挂接 + BOM: 按部位+标高给每根杆件挂规格 (004/005/007/008/010/013/110 明细表实测, 中段插值估)"""
import json, math, re
from collections import defaultdict

ANGLE = {'L45x4': 2.74, 'L63x5': 4.82, 'L75x3': 3.48, 'L75x5': 5.82, 'L75x6': 6.91,
         'L80x6': 7.28, 'L80x7': 8.41, 'L90x6': 8.23, 'L90x7': 9.51, 'L100x7': 10.83,
         'L110x7': 11.93, 'L125x8': 15.50, 'L125x12': 22.54, 'L140x10': 20.98,
         'L160x10': 24.34, 'L180x12': 32.96, 'L200x14': 42.86, 'L220x24': 78.8}
TUBE = {'φ480x10': 115.06, 'φ530x12': 153.03, 'φ550x12': 159.57, 'φ660x14': 223.39}

def unit_mass(spec):
    """单重 kg/m: 查表优先, 缺项按公式兜底 (角钢/钢管, 精度 ~3%)"""
    u = ANGLE.get(spec) or TUBE.get(spec)
    if u: return u
    s = spec.lower().replace('×', 'x')
    m = re.match(r'l(\d{2,3})x(\d{1,2})$', s)
    if m:
        w, t = int(m.group(1)), int(m.group(2))
        return round(0.00785 * t * (2*w - t), 2)
    m = re.match(r'φ(\d{3})x(\d{1,2})$', s)
    if m:
        d, t = int(m.group(1)), int(m.group(2))
        return round(0.02466 * t * (d - t), 2)
    return None

def _spec_for(m):
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

def attach(frame):
    ms = frame['members']
    n_att = 0
    for m in ms:
        spec, note = _spec_for(m)
        m['spec'] = spec
        m['spec_note'] = note
        m['len_mm'] = round(math.dist(m['p1'], m['p2']), 1)
        uw = ANGLE.get(spec) or TUBE.get(spec)
        m['unit_kg'] = uw
        m['wt_kg'] = round(uw * m['len_mm'] / 1000, 1) if uw else None
        if uw: n_att += 1
    frame['meta']['spec_level'] = '粗略: 规格来自明细表OCR, 中段为插值估算'
    return n_att

def attach_generic(frame, rows_path):
    """通用解析路径的规格挂接: 行池按长度匹配, 未命中按角色默认估算"""
    ms = frame['members']
    for m in ms:
        m['len_mm'] = round(math.dist(m['p1'], m['p2']), 1)
    pool = []  # (spec, len)
    try:
        rows_by = json.load(open(rows_path, encoding='utf-8'))
        for rows in rows_by.values():
            for r in rows:
                if r.get('chk') is False: continue  # 新解析器: 校验不过的行是 OCR 噪声
                sp, ln = r.get('spec'), r.get('len')
                if sp and isinstance(ln, (int, float)) \
                        and re.match(r'^[LlΦφ]\d', str(sp)):
                    pool.append((str(sp), float(ln)))
    except (OSError, ValueError):
        pass
    def pick(len_mm):
        best = None
        for sp, ln in pool:
            if abs(ln - len_mm) <= max(20.0, 0.02*len_mm):
                best = sp
                break
        return best
    # 角色默认: 主材取行池最大角钢, 斜材/横隔取常用小规格
    big = max((sp for sp, _ in pool if re.match(r'^L\d+x\d+$', sp)),
              key=lambda s: ANGLE.get(s, 0), default='L125x8')
    n_att = 0
    for m in ms:
        spec = pick(m['len_mm'])
        if spec:
            note = '长度匹配'
        else:
            if m['mid'].startswith('LEG'):
                spec = big
            elif m['mid'].startswith('DIA'):
                spec = 'L45x4'
            elif m['mid'].startswith(('BR', 'XB', 'VG')):
                spec = 'L63x5'
            else:
                spec = 'L63x5'
            note = '估'
        m['spec'] = spec
        m['spec_note'] = note
        uw = ANGLE.get(spec) or TUBE.get(spec)
        m['unit_kg'] = uw
        m['wt_kg'] = round(uw * m['len_mm'] / 1000, 1) if uw else None
        if uw: n_att += 1
    frame['meta']['spec_level'] = '不可靠: 通用解析, 规格为长度匹配或角色默认估计'
    return n_att


def write_bom(frame, path, members=None):
    """BOM 按图纸件号汇总 (匹配后调用); 未对应杆件按估算规格列在末尾"""
    ms = members if members is not None else frame['members']
    groups = {}
    for m in ms:
        no = str(m.get('piece_no') or '-')
        k = (no, m['spec'], m.get('len_row'))
        g = groups.setdefault(k, {'n': 0, 'wt': 0.0,
                                  'qty_row': m.get('qty_row'),
                                  'src': m.get('spec_src') or m.get('spec_note', '')})
        g['n'] += 1
        if m.get('wt_kg'): g['wt'] += m['wt_kg']
    rows = sorted(groups.items(),
                  key=lambda kv: (kv[0][0] == '-',
                                  int(kv[0][0]) if kv[0][0].isdigit() else 10**9,
                                  kv[0][1]))
    with open(path, 'w', encoding='utf-8-sig') as f:
        f.write('件号,规格,单长mm,数量,图面数量,单重kg,总重kg,来源\n')
        for (no, spec, lr), g in rows:
            f.write(f'{no},{spec},{lr if lr else ""},{g["n"]},'
                    f'{g["qty_row"] if g["qty_row"] else ""},'
                    f'{g["wt"]/g["n"]:.2f},{g["wt"]:.1f},{g["src"]}\n')
    return rows, sum(g['wt'] for _, g in rows)
