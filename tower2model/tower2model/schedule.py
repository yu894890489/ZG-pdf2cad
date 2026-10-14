# -*- coding: utf-8 -*-
"""明细表行解析: OCR 文本 -> 行(y 聚类) -> 编号/规格/长度/数量"""
import os, re, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SPEC_RE = re.compile(r'(L?\d{2,3}[Xx×]\d{1,2}(?:[Xx×]\d{1,2})?|[Gg]\d+[-.]?\d*|-?\d+[Xx×]\d+)')

def _load_txt(path):
    rows = []
    for ln in open(path, encoding='utf-8'):
        p = ln.split()
        if len(p) < 4: continue
        try: rows.append((float(p[0]), float(p[1]), float(p[2]), p[3]))
        except ValueError: continue
    return rows

def parse_row(tokens):
    """tokens: [(x, text)] 一行内的文字块 -> (no, spec, len, qty)"""
    num = spec = None; nums = []
    for x, t in tokens:
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

# ---------- 表格锚定解析 (构件明细表) ----------
# 全页 y 聚类会把尺寸链/螺栓表/法兰标注全收进行池 (SZK 165 图 4756 行里 >95% 是垃圾)。
# 明细表版式固定: 一列规格 (LxxXxx / -xXxx / φxxxXx) 纵向对齐, 左邻件号, 右邻
# 长度/数量/单重/总重。先找规格列 x 锚, 再按行组装, 最后用单重=理论重量 交叉校验。
SPEC_TOK = re.compile(
    r'(?:Q\d{3})?\s*(?:L\d{2,3}|-\d{1,3}|Φ\d{3}|φ\d{3}|0\d{3})\s*[Xx×]\s*\d{1,3}(?:\.\d)?(?:-?Q\d{3})?')
# 注: 0\d{3} 是钢管规格的 OCR 变体 —— RapidOCR 把 φ 识别成 0
# ('Q355φ245X5' -> 'Q3550245X5'), SZK 下部塔身全是钢管段, 缺这个变体整批钢管行丢失

def _clean_spec(t):
    """'Q355L125X12' -> 'L125x12'; 'Q4200660X14' -> 'φ660x14' (φ 被 OCR 成 0)"""
    m = re.search(r'(L\d{2,3}|-\d{1,3}|Φ\d{3}|φ\d{3}|0\d{3})\s*[Xx×]\s*(\d{1,3}(?:\.\d)?)', t)
    if not m: return None
    head = m.group(1)
    if re.match(r'^0\d{3}$', head): head = 'φ' + head[1:]
    return f'{head}x{m.group(2)}'.lower()

def _num(t):
    try:
        v = float(t.replace('C', '').replace('|', '.').replace('@', '.'))
        return v
    except ValueError:
        return None

def kg_m(spec, length_mm=1000.0):
    """规格单重 kg (给 length_mm 长的料)。角钢/钢板用公式, 精度 ~3%, 只作校验。"""
    s = spec.lower().replace('×', 'x')
    m = re.match(r'l(\d{2,3})x(\d{1,2})$', s)
    if m:
        w, t = int(m.group(1)), int(m.group(2))
        return 0.00785 * t * (2*w - t) * length_mm / 1000.0
    m = re.match(r'-(\d{1,3})x(\d{1,3})$', s)
    if m:
        t, w = int(m.group(1)), int(m.group(2))
        return 0.00785 * t * w * length_mm / 1000.0
    m = re.match(r'φ(\d{3})x(\d{1,2})$', s)
    if m:
        d, t = int(m.group(1)), int(m.group(2))
        return 0.02466 * t * (d - t) * length_mm / 1000.0
    return None

def _find_spec_col(tokens):
    """找规格列: 规格 token 按 x 连续聚类(带宽±45), 带内数量最多者 -> (x, spec_tokens)"""
    cols = find_spec_cols(tokens)
    if not cols: return None, []
    return cols[0]

def find_spec_cols(tokens):
    """全部规格列候选 [(x, spec_tokens)], 按分数降序。
    一页可有多个表 (钢管段图: 构件明细表钢管列 + 垫板表钢板列), 只取最优会丢整表"""
    toks = sorted(((x, y, t) for y, x, c, t in tokens if SPEC_TOK.fullmatch(t)))
    groups = []
    for x, y, t in toks:
        if groups and x - groups[-1][-1][0] <= 45:
            groups[-1].append((x, y, t))
        else:
            groups.append([(x, y, t)])
    cols = []
    for g in groups:
        if len(g) < 5: continue
        xs = [x for x, _, _ in g]
        ys = [y for _, y, _ in g]
        score = len(g) + (max(ys) - min(ys)) / 200.0
        cols.append((score, sum(xs)/len(xs), [(y, x, t) for x, y, t in g]))
    cols.sort(key=lambda c: -c[0])
    return [(x, toks) for _, x, toks in cols]

def parse_table(tokens, yt=None):
    """整页 OCR tokens [(y,x,conf,text)] -> 明细表行列表 (找不到规格列返回 [])
    遍历全部规格列候选(一页可有构件表+垫板表两列), 行按 (y,spec) 去重"""
    if yt is None: yt = 14
    rows = []
    seen = set()
    for spec_x, spec_toks in find_spec_cols(tokens):
        for r in _parse_col(tokens, spec_x, spec_toks, yt):
            k = (r['y'], r['spec'])
            if k in seen: continue
            seen.add(k)
            rows.append(r)
    return rows

def _parse_col(tokens, spec_x, spec_toks, yt):
    rows = []
    for sy, sx, st in spec_toks:
        band = [(x, t) for y, x, c, t in tokens if abs(y - sy) <= yt]
        band.sort()
        no = ln = qty = None; unit = total = None
        note_r = []
        ln_x = qty_x = unit_x = -1e9
        for x, t in band:
            if abs(x - sx) <= 40 and x != sx: continue  # 规格列自身(去重)
            v = _num(t)
            if x < sx - 30:
                if no is None and v is not None and v == int(v) and 1 <= v <= 9999:
                    no = str(int(v))
            elif x > sx + 40:
                if v is None:
                    note_r.append((x, t)); continue
                if ln is None and v == int(v) and 100 <= v <= 15000:
                    ln = int(v); ln_x = x
                elif ln is not None and x > ln_x and qty is None and v == int(v) and 0 <= v <= 99:
                    qty = int(v); qty_x = x
                elif qty is not None and x > qty_x and 0 < v <= 999:
                    if unit is None: unit = v; unit_x = x
                    elif total is None: total = v
        note = ' '.join(t for _, t in sorted(note_r))
        ok = False
        if unit and ln:
            th = kg_m(_clean_spec(st) or '', ln)
            ok = th is not None and abs(unit - th) <= max(0.15, 0.08 * th)
        rows.append({'y': round(sy, 1), 'no': no, 'spec': _clean_spec(st),
                     'len': ln, 'qty': qty, 'unit': unit, 'total': total,
                     'note': note[:30], 'chk': ok,
                     'raw': ' '.join(t for _, t in band)[:90]})
    return rows

def parse_sheet(ocr_txt, dpi=200):
    toks = _load_txt(ocr_txt)
    yt = 14 * (dpi / 200.0)
    table = parse_table(toks, yt)
    if table:
        n_ok = sum(1 for r in table if r['chk'])
        # 校验通过率过半才认定是明细表, 否则退回全页聚类
        if n_ok >= max(3, len(table) * 0.5):
            return table
    lines = cluster(toks, yt)
    out = []
    for L in lines:
        L['items'].sort()
        no, spec, ln, qty = parse_row(L['items'])
        if spec and no:
            out.append({'y': round(L['y'], 1), 'no': no, 'spec': spec,
                        'len': ln, 'qty': qty,
                        'raw': ' '.join(t for _, t in L['items'])[:90]})
    return out

def parse_all(ocr_dir, dpi=200):
    """目录内所有 ocrNNN.txt -> {sheet: [rows]}"""
    import glob
    out = {}
    for p in sorted(glob.glob(os.path.join(ocr_dir, 'ocr*.txt'))):
        name = os.path.basename(p)
        if not name.startswith('ocr') or not name[3:6].isdigit(): continue
        s = name[3:6]
        out[s] = parse_sheet(p, dpi)
    return out
