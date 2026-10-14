# -*- coding: utf-8 -*-
"""拆件/下料: 端头分类回退留缝 + 明细表件号匹配
缝隙语义: 端面到对方杆面净隙 >= GAP (不是胶囊球端不侵入)
  - 共点斜交端回退 (R_other+GAP)/sinθ; 近共线对接(sinθ<0.26)各回退 GAP/2
  - 端点触对方杆身: 回退 (R_other+GAP-da)/sinθ; 钳位 [0, MAX_TRIM]
件号匹配三档: spec+len(±60) -> len 驱动(±120, 规格取图纸真值, 单重接近估算仲裁) -> spec~len(±300 唯一近邻)
"""
import os, re, json, math
import numpy as np

from . import specs as _specs

GAP_MM = 3.0
TOL_NODE = 2.0
MAX_TRIM = 500.0
BUTT_SIN = 0.26

def _seg_pt_dist(p, a, b):
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / max(ab @ ab, 1e-9), 0.0, 1.0)
    return float(np.linalg.norm(p - (a + t * ab)))

def classify_and_trim(members, gap=GAP_MM):
    P1 = [np.array(m['p1'], float) for m in members]
    P2 = [np.array(m['p2'], float) for m in members]
    R = [m['r_mm'] for m in members]
    U = [(b - a) / max(np.linalg.norm(b - a), 1e-9) for a, b in zip(P1, P2)]
    N = len(members)
    trims = [[0.0, 0.0] for _ in range(N)]
    kinds = [['FREE', 'FREE'] for _ in range(N)]
    for i in range(N):
        for e, p in ((0, P1[i]), (1, P2[i])):
            best_t = best_n = 0.0
            for j in range(N):
                if j == i: continue
                de = min(np.linalg.norm(p - P1[j]), np.linalg.norm(p - P2[j]))
                sin_t = float(np.linalg.norm(np.cross(U[i], U[j])))
                if de < TOL_NODE:
                    d = gap / 2.0 if sin_t < BUTT_SIN else (R[j] + gap) / sin_t
                    d = min(max(d, gap / 2.0), MAX_TRIM)
                    if d > best_n: best_n, kinds[i][e] = d, 'NODE'
                else:
                    da = _seg_pt_dist(p, P1[j], P2[j])
                    if da < R[j] + gap:
                        d = (R[j] + gap - da) / max(sin_t, 0.05)
                        d = min(max(d, 0.0), MAX_TRIM)
                        if d > best_t: best_t, kinds[i][e] = d, 'TJOINT'
            trims[i][e] = max(best_t, best_n)
    return trims, kinds

def apply_gaps(members, gap=GAP_MM, in_place=False):
    trims, kinds = classify_and_trim(members, gap)
    out = members if in_place else [dict(m) for m in members]
    for m, (t1, t2), (k1, k2) in zip(out, trims, kinds):
        a, b = np.array(m['p1'], float), np.array(m['p2'], float)
        u = (b - a) / max(np.linalg.norm(b - a), 1e-9)
        a1, b1 = a + u * t1, b - u * t2
        m['p1t'] = [round(v, 1) for v in a1]
        m['p2t'] = [round(v, 1) for v in b1]
        m['trim1_mm'], m['trim2_mm'] = round(t1, 1), round(t2, 1)
        m['end_kind'] = f'{k1}/{k2}'
        m['cut_len_mm'] = round(float(np.linalg.norm(b1 - a1)), 1)
    return out

# ---------------- 件号 ----------------
def _norm_spec(s):
    if not s: return None
    s = s.lower().replace('×', 'x')
    m = re.search(r'l(\d{2,3})x(\d{1,2})', s)
    if m:
        w, t = int(m.group(1)), int(m.group(2))
        if t > w * 0.3 + 2: return None  # 厚于 w/3 的"角钢"是 OCR 粘连垃圾 (如 L42x19)
        return f'L{w}x{t}'
    m = re.search(r'[φΦ](\d{3})x(\d{1,2})', s)
    if m: return f'φ{m.group(1)}x{m.group(2)}'
    m = re.search(r'\b(480|530|550|660)x(\d{1,2})\b', s)
    if m: return f'φ{m.group(1)}x{m.group(2)}'
    m = re.search(r'(?<![-\d])(\d{2,3})x(\d{1,2})(?!\d)', s)
    if m and 40 <= int(m.group(1)) <= 250 and 3 <= int(m.group(2)) <= 30:
        return f'L{m.group(1)}x{m.group(2)}'
    return None

def load_rows(schedule_rows_path):
    """schedule_rows json -> 统一行列表 (高优先级文件放后覆盖)。
    只收角钢/钢管行且单重校验通过 (chk): 钢板是垫板/法兰不在模型上且撞件号,
    校验不过的行规格/长度常是 OCR 噪声, 进池会污染规格"""
    by_key = {}
    for fn in schedule_rows_path:
        if not fn or not os.path.exists(fn): continue
        d = json.load(open(fn, encoding='utf-8'))
        for sheet, items in d.items():
            for r in items:
                if not r.get('chk'): continue
                no = str(r.get('no') or '')
                if not no.isdigit(): continue  # 件号缺失
                # 注: 不再按 no 大小过滤 —— SZK 钢管段真件号就是 4xxx~6xxx 号段,
                # 行质量由 chk (单重=理论重量自洽) 保证
                sp = _norm_spec(r['spec'])
                if not sp or sp[0] not in 'Lφ': continue
                by_key[(sheet, no, sp)] = {
                    'sheet': sheet, 'no': no, 'spec': sp,
                    'len': r['len'], 'qty': r['qty'], 'left': r['qty'] or 99}
    return list(by_key.values())

PREF = {'L1': ['004'], 'L2': ['007'], 'L3': ['010']}

def _accept(m, r, lvl):
    r['left'] -= 1
    m['piece_no'] = str(r['no'])
    m['piece_src'] = f"{r['sheet']}({lvl})"
    m['len_row'] = r['len']
    m['qty_row'] = r.get('qty')
    if r['spec'] != m['spec']:  # 图纸规格为真值, 覆盖估算
        m['spec'] = r['spec']
        m['spec_src'] = '图纸明细表'
        u = _specs.unit_mass(r['spec'])
        m['unit_kg'] = u
        m['wt_kg'] = round(u * m['len_mm'] / 1000, 1) if u else None

def _pick(rows, pred):
    """left>0 优先, 不足时允许超配 (模型分段粒度与图纸件号不一一对应)"""
    ok = [r for r in rows if pred(r) and r['left'] > 0]
    if ok: return ok
    return [r for r in rows if pred(r)]

def match_pieces(members, rows):
    """三档匹配:
    1) 估算规格+len±60; 2) len±30 紧窗且候选规格唯一(规格取图纸真值);
    3) 估算规格 len±300 唯一近邻。行池数量软约束 (left 优先, 允许超配)。"""
    all_sheets = sorted({r['sheet'] for r in rows})
    for r in rows:
        r.setdefault('left', r['qty'] or 99)
    n_ok = 0
    def _hit(m, r, lvl):
        nonlocal n_ok
        _accept(m, r, lvl)
        n_ok += 1
    # Pass1: 估算规格 + len±60 (部位图纸优先)
    rest = []
    for m in members:
        pref = PREF.get(m['mid'][:2], [])
        L0 = m.get('len_mm', 0)
        cand = None
        pool = _pick(rows, lambda r: r['spec'] == m['spec'] and r['len']
                     and abs(r['len'] - L0) <= 60)
        for sh in pref + [s for s in all_sheets if s not in pref]:
            for r in pool:
                if r['sheet'] == sh:
                    if cand is None or abs(r['len'] - L0) < abs(cand['len'] - L0):
                        cand = r
            if cand: break
        if cand: _hit(m, cand, 'spec+len')
        else: rest.append(m)
    # Pass2: len±45 紧窗, 候选规格唯一才收 (规格取图纸真值);
    # 按 sheet 内评估 —— 钢管段节间重复结构使同长行跨多图重复, 全局判唯一会整批弃权;
    # 单重比门限防"同长异材"错配 —— 角钢候选 [0.4,2.5] (估算规格有部位实测依据, 不会差 3 倍量级);
    # 钢管候选 [0.15,6.5] (SZK 下部塔身估算表臆造成角钢, 真值钢管单重 2~6 倍, 门限须放行)
    rest2 = []
    for m in rest:
        L0 = m.get('len_mm', 0)
        e = _specs.unit_mass(m['spec']) or 5.0
        hits = []  # (sheet, row) 各 sheet 内规格唯一的最佳行
        for sh in all_sheets:
            pool = _pick(rows, lambda r: r['sheet'] == sh
                         and r['len'] and abs(r['len'] - L0) <= 45
                         and r['spec'][0] in 'Lφ'
                         and (0.15 if r['spec'][0] == 'φ' else 0.4)
                             <= (_specs.unit_mass(r['spec']) or e) / e
                             <= (6.5 if r['spec'][0] == 'φ' else 2.5))
            if pool and len({r['spec'] for r in pool}) == 1:
                hits.append(min(pool, key=lambda r: abs(r['len'] - L0)))
        if hits:
            _hit(m, min(hits, key=lambda r: (abs(r['len'] - L0), r['sheet'])), 'len'); continue
        rest2.append(m)
    # Pass3: 估算规格 len±300, sheet 内唯一近邻 (同 Pass2, 节间重复行按 sheet 隔离)
    for m in rest2:
        L0 = m.get('len_mm', 0)
        hits = []
        for sh in all_sheets:
            pool = _pick(rows, lambda r: r['sheet'] == sh
                         and r['spec'] == m['spec'] and r['len']
                         and abs(r['len'] - L0) <= 300)
            if pool:
                best = min(pool, key=lambda r: abs(r['len'] - L0))
                nb = sum(1 for r in pool if abs(abs(r['len'] - L0) - abs(best['len'] - L0)) <= 30)
                if nb == 1:
                    hits.append(best)
        if hits:
            _hit(m, min(hits, key=lambda r: (abs(r['len'] - L0), r['sheet'])), 'spec~len'); continue
        # Pass4: 长杆(≥3000)估算规格失准救援 — 单重量级相近 + len±400
        # sheet 内明显唯一近邻 (次近隔>120), 估算表对长杆的规格/长度都常错;
        # 钢管候选单重门限放宽 (钢管段估算表臆造, 同 Pass2)
        L0 = m.get('len_mm', 0)
        if L0 >= 3000:
            e = _specs.unit_mass(m['spec']) or 5.0
            hits = []
            for sh in all_sheets:
                pool = _pick(rows, lambda r: r['sheet'] == sh
                             and r['len'] and abs(r['len'] - L0) <= 400
                             and r['spec'][0] in 'Lφ'
                             and (0.15 if r['spec'][0] == 'φ' else 0.5)
                                 <= (_specs.unit_mass(r['spec']) or e) / e
                                 <= (6.5 if r['spec'][0] == 'φ' else 2.0))
                if pool:
                    best = min(pool, key=lambda r: abs(r['len'] - L0))
                    second = min((abs(r['len'] - L0) for r in pool if r['no'] != best['no']),
                                 default=9999)
                    if abs(best['len'] - L0) < second - 120:
                        hits.append(best)
            if hits:
                _hit(m, min(hits, key=lambda r: (abs(r['len'] - L0), r['sheet'])), 'len~'); continue
        # Pass5: 长杆系统偏差救援 — builtin 参数化重建与图纸有 ~6% 系统长度偏差,
        # 绝对窗口够不着; len±8% 且 sheet 内规格唯一最近邻, 次近隔 >4% 防歧义
        if L0 >= 3000:
            e = _specs.unit_mass(m['spec']) or 5.0
            hits = []
            for sh in all_sheets:
                pool = _pick(rows, lambda r: r['sheet'] == sh
                             and r['len'] and abs(r['len'] - L0) <= 0.08 * L0
                             and r['spec'][0] in 'Lφ'
                             and (0.15 if r['spec'][0] == 'φ' else 0.4)
                                 <= (_specs.unit_mass(r['spec']) or e) / e
                                 <= (6.5 if r['spec'][0] == 'φ' else 2.5))
                if pool and len({r['spec'] for r in pool}) == 1:
                    best = min(pool, key=lambda r: abs(r['len'] - L0))
                    second = min((abs(r['len'] - L0) for r in pool if r['no'] != best['no']),
                                 default=9999)
                    if second - abs(best['len'] - L0) > 0.04 * L0:
                        hits.append(best)
            if hits:
                _hit(m, min(hits, key=lambda r: (abs(r['len'] - L0), r['sheet'])), 'len±8%'); continue
        m['piece_no'] = None
        m['piece_src'] = None
    return n_ok

def write_cut_list(members, path):
    groups = {}
    for m in members:
        k = (m.get('piece_no') or '-', m['spec'], round(m['cut_len_mm']))
        g = groups.setdefault(k, {'n': 0, 'roles': set()})
        g['n'] += 1
        g['roles'].add(m['role'])
    with open(path, 'w', encoding='utf-8-sig') as f:
        f.write('件号,规格,下料长mm,数量,部位\n')
        for (no, spec, L), g in sorted(groups.items(), key=lambda kv: (kv[0][0] == '-', kv[0][1], kv[0][2])):
            f.write(f"{no},{spec},{L},{g['n']},{'/'.join(sorted(g['roles']))[:40]}\n")
    return len(groups)
