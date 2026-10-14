# -*- coding: utf-8 -*-
"""从 OCR 结果聚类明细表行: 编号/规格/长度/数量/单重/总重"""
import sys, re, json, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def load(num, suffix=''):
    rows = []
    fn = f'demo/ocr{num}{suffix}.txt'
    if not os.path.exists(fn): return rows
    for ln in open(fn, encoding='utf-8'):
        p = ln.split()
        if len(p) < 4: continue
        try: rows.append((float(p[0]), float(p[1]), float(p[2]), p[3]))
        except ValueError: continue
    return rows

# 用法: parse_schedule.py [_300] num...  (_300 = 读 ocrNNN_300.txt, 聚类容差按 300dpi 缩放)
SUFFIX = ''
_args = sys.argv[1:]
if _args and _args[0].startswith('_'):
    SUFFIX = _args[0]; _args = _args[1:]
SHEETS = _args if _args else ['004', '005', '008', '010', '013', '102']
YT = 14 * (int(SUFFIX.lstrip('_') or 200) / 200.0)   # 行聚类容差随 DPI 缩放

SPEC_RE = re.compile(r'(L?\d{2,3}[Xx×]\d{1,2}(?:[Xx×]\d{1,2})?|[Gg]\d+[-.]?\d*|-?\d+[Xx×]\d+)')

def parse_row(tokens):
    """tokens: [(x, text)] 一行内的文字块"""
    num = spec = None; nums = []
    for x, t in tokens:
        # 合并块: 编号+材质+规格
        m = re.match(r'^(\d{2,4})(?:C\d+)?((?:L|Φ|φ|G)?[\d.]+[Xx×][\d.]+.*)$', t)
        if m and not spec:
            num = m.group(1); spec = m.group(2).replace('X', 'x'); continue
        m2 = SPEC_RE.search(t)
        if m2 and not spec and len(t) <= 20:
            spec = m2.group(1).replace('X', 'x'); continue
        if re.fullmatch(r'\d{2,4}', t) and num is None:
            num = t; continue
        try:
            v = float(t.replace('C', '').replace('|', '.').replace('@', '.'))
            nums.append((x, v))
        except ValueError:
            pass
    # 数字按 x 排序: 通常 长度(大), 数量(小), 单重(小数), 总重
    nums.sort()
    length = qty = None
    for x, v in nums:
        if qty is None and 0 < v <= 200 and v == int(v): qty = int(v)
    for x, v in reversed(nums):
        if length is None and 300 <= v <= 15000 and v == int(v): length = int(v)
    return num, spec, length, qty

def cluster(rows, yt=14):
    rows = sorted(rows, key=lambda r: -r[0])
    lines = []
    for y, x, c, t in rows:
        for L in lines:
            if abs(L['y'] - y) <= yt:
                L['items'].append((x, t)); L['y'] = (L['y']*len(L['items'])+y)/(len(L['items'])+1)
                break
        else:
            lines.append({'y': y, 'items': [(x, t)]})
    return lines

# 用法: parse_schedule.py [_300] num...  (_300 = 读 ocrNNN_300.txt, 行聚类容差随 DPI 缩放)
SUFFIX = ''
_args = sys.argv[1:]
if _args and _args[0].startswith('_'):
    SUFFIX = _args[0]; _args = _args[1:]
SHEETS = _args if _args else ['004', '005', '008', '010', '013', '102']
YT = 14 * (int(SUFFIX.lstrip('_') or 200) / 200.0)
out = {}
for num in SHEETS:
    lines = cluster(load(num, SUFFIX), YT)
    table = []
    for L in lines:
        L['items'].sort()
        num_i, spec, length, qty = parse_row(L['items'])
        if spec and num_i:
            table.append({'y': round(L['y'], 1), 'no': num_i, 'spec': spec,
                          'len': length, 'qty': qty,
                          'raw': ' '.join(t for _, t in L['items'])[:90]})
    out[num] = table
    print(f'--- {num}: {len(table)} rows')
    for r in table[:14]:
        print(f"  {r['no']:>4} {r['spec']:<14} len={r['len']} qty={r['qty']}  | {r['raw'][:60]}")
json.dump(out, open(f'demo/schedule_rows{SUFFIX}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'saved demo/schedule_rows{SUFFIX}.json')
