# -*- coding: utf-8 -*-
"""拆件/下料 v1 (2026-09-30): frame.json -> 每根杆件 = 独立下料型材
1. 端头分类: 共点(NODE) / 端点触对方轴线(TJOINT) / 自由端(FREE); 杆中 X 交叉不裁(设计搭接点)
2. 连接缝隙 GAP(默认3mm, --gap 可配 / fab.GAP_MM 可导入):
   - T 头(腹杆端点落在弦杆轴线上): 端点沿自身轴回退 (r_other+GAP)/sinθ
   - 共点(两杆端点重合): 各回退 (r_other+GAP/2)/sinθ
   - 近共线对接(sinθ<0.26, 弦杆接续): 面对面各回退 GAP/2
   回退量钳位 [GAP/2, 500]
3. 件号: 按明细表(004/007/010/013)以 规格+长度(±20mm) 匹配, qty 消耗制;
   优先部位对应图纸(L1->004, L2->007, L3->010, 其余->013), 次选全局
输出: demo/frame_fab.json (带 p1t/p2t 裁后坐标+件号+回退量)
      demo/cut_list.csv (下料清单: 件号/规格/下料长/数量)
      demo/tower_frame_fab.scad + demo/fab_check.png (缝隙目检)
"""
import sys, os, json, math, re, argparse
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np

GAP_MM = 3.0          # 连接净隙, --gap 覆盖
TOL_NODE = 2.0        # 端点重合判据 mm
TOL_T = 5.0           # 端点落在对方轴线判据 mm
MAX_TRIM = 500.0      # 回退上限(浅角度保护)
BUTT_SIN = 0.26       # sinθ 低于此 = 近共线对接

def _seg_pt_dist(p, a, b):
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / max(ab @ ab, 1e-9), 0.0, 1.0)
    return float(np.linalg.norm(p - (a + t * ab)))

def classify_and_trim(members, gap=GAP_MM):
    """返回 (trims[i][2端], kinds[i][2端]) 就地不修改; trims 单位 mm"""
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
                    # 共点: 近共线=平口对接(各让半缝); 斜交=端面距对方杆面留缝
                    d = gap / 2.0 if sin_t < BUTT_SIN else (R[j] + gap) / sin_t
                    d = min(max(d, gap / 2.0), MAX_TRIM)
                    if d > best_n: best_n, kinds[i][e] = d, 'NODE'
                else:
                    # 端头面侵入对方杆身(轴距<R_j+GAP) -> 回退使 轴距=R_j+GAP
                    da = _seg_pt_dist(p, P1[j], P2[j])
                    if da < R[j] + gap:
                        d = (R[j] + gap - da) / max(sin_t, 0.05)
                        d = min(max(d, 0.0), MAX_TRIM)
                        if d > best_t: best_t, kinds[i][e] = d, 'TJOINT'
            trims[i][e] = max(best_t, best_n)
    return trims, kinds

def apply_gaps(members, gap=GAP_MM, in_place=False):
    """对 members 计算 + 应用端头回退; 返回 members (含 p1t/p2t 与裁后 len_mm)"""
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

# ---------------- 件号匹配 ----------------
def _norm_spec(s):
    if not s: return None
    s = s.lower().replace('×', 'x')
    m = re.search(r'l(\d{2,3})x(\d{1,2})', s)
    if m: return f'L{m.group(1)}x{m.group(2)}'
    m = re.search(r'[φΦ](\d{3})x(\d{1,2})', s)
    if m: return f'φ{m.group(1)}x{m.group(2)}'
    # OCR 丢前缀补救: 钢管 480/530/550/660x壁厚
    m = re.search(r'\b(480|530|550|660)x(\d{1,2})\b', s)
    if m: return f'φ{m.group(1)}x{m.group(2)}'
    # 角钢丢 L 前缀: 宽40~250 x 厚3~30 (避免误吃钢板 -t x w)
    m = re.search(r'(?<![-\d])(\d{2,3})x(\d{1,2})(?!\d)', s)
    if m and 40 <= int(m.group(1)) <= 250 and 3 <= int(m.group(2)) <= 30:
        return f'L{m.group(1)}x{m.group(2)}'
    return None

def load_schedule(*suffixes):
    """合并多个 schedule_rows 后缀文件; 同图同号同规格行高优先级覆盖低(_300 优先于 '')"""
    by_key = {}
    for suf in suffixes:                      # 后写的覆盖先写的 -> 把高优先级放后面
        if suf is None: continue
        fn = f'demo/schedule_rows{suf}.json'
        if suf and not os.path.exists(fn): continue
        d = json.load(open(fn, encoding='utf-8'))
        for sheet, items in d.items():
            for r in items:
                sp = _norm_spec(r['spec'])
                if not sp: continue
                by_key[(sheet, str(r['no']), sp)] = {
                    'sheet': sheet, 'no': r['no'], 'spec': sp,
                    'len': r['len'], 'qty': r['qty'], 'left': r['qty'] or 99}
    return list(by_key.values())

PREF = {'L1': ['004'], 'L2': ['007'], 'L3': ['010']}

def match_pieces(members, rows):
    """qty 消耗制匹配; 件号全塔统一编号 -> spec+len 全局匹配, spec 级仅限本部位图纸"""
    all_sheets = sorted({r['sheet'] for r in rows})
    n_ok = 0
    for m in members:
        tag = m['mid'][:2]
        pref = PREF.get(tag, [])
        cand = None
        # spec+len(强, 全局) -> spec(弱, 仅本部位图纸) -> spec+近长(±300, 全局须唯一近邻)
        for lvl, sheets in (('spec+len', pref + [s for s in all_sheets if s not in pref]),
                            ('spec', pref)):
            for sh in sheets:
                for r in rows:
                    if r['sheet'] != sh or r['left'] <= 0 or r['spec'] != m['spec']: continue
                    if lvl == 'spec+len':
                        if r['len'] and abs(r['len'] - m.get('len_mm', 0)) <= 20:
                            cand = (lvl, r); break
                    elif not cand:
                        cand = (lvl, r)
                if cand: break
            if cand: break
        if not cand:
            # 近似档: 同规格、|Δlen|<=300 且该行是唯一近邻(避免乱认)
            L0 = m.get('len_mm', 0)
            near = [r for r in rows if r['left'] > 0 and r['spec'] == m['spec']
                    and r['len'] and abs(r['len'] - L0) <= 300]
            if near:
                best = min(near, key=lambda r: abs(r['len'] - L0))
                nb = sum(1 for r in near if abs(abs(r['len'] - L0) - abs(best['len'] - L0)) <= 30)
                if nb == 1:
                    cand = ('spec~len', best)
        if cand:
            lvl, r = cand
            r['left'] -= 1
            m['piece_no'] = r['no']
            m['piece_src'] = f"{r['sheet']}({lvl})"
            n_ok += 1
        else:
            m['piece_no'] = None
            m['piece_src'] = None
    return n_ok

# ---------------- 主流程 ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gap', type=float, default=GAP_MM)
    ap.add_argument('--rows', default='', help='schedule_rows 后缀, 如 _300')
    args = ap.parse_args()
    gap = args.gap

    frame = json.load(open('demo/frame.json', encoding='utf-8'))
    ms = frame['members']
    print(f'source: {len(ms)} members, gap={gap}mm')

    ms = apply_gaps(ms, gap)
    for m in ms:
        m['len_mm'] = m['cut_len_mm']          # 重量/清单用裁后长度

    suffixes = [args.rows, ''] if args.rows else ['']   # _300 优先, 200dpi 兜底
    rows = load_schedule(*suffixes)
    n_ok = match_pieces(ms, rows)
    print(f'件号匹配: {n_ok}/{len(ms)}')

    from collections import Counter
    print('端头类型:', Counter(k for m in ms for k in m['end_kind'].split('/')))
    tr = [t for m in ms for t in (m['trim1_mm'], m['trim2_mm']) if t > 0]
    print(f'回退端数: {len(tr)}, 平均 {sum(tr)/len(tr):.1f}mm, 最大 {max(tr):.1f}mm')
    hit = Counter(f"{m['piece_src']}" for m in ms if m['piece_no'])
    print('件号来源:', dict(hit))

    meta = dict(frame['meta'])
    meta['gap_mm'] = gap
    meta['fab_level'] = 'v1拆件: 端头回退留缝+明细表件号匹配(部分件号待补OCR)'
    json.dump({'meta': meta, 'members': ms},
              open('demo/frame_fab.json', 'w', encoding='utf-8'), ensure_ascii=False)

    # ---- 下料清单 ----
    groups = {}
    for m in ms:
        k = (m['piece_no'] or '-', m['spec'], round(m['cut_len_mm']))
        g = groups.setdefault(k, {'n': 0, 'roles': set()})
        g['n'] += 1
        g['roles'].add(m['role'])
    with open('demo/cut_list.csv', 'w', encoding='utf-8-sig') as f:
        f.write('件号,规格,下料长mm,数量,部位\n')
        for (no, spec, L), g in sorted(groups.items(), key=lambda kv: (kv[0][0] == '-', kv[0][1], kv[0][2])):
            f.write(f"{no},{spec},{L},{g['n']},{'/'.join(sorted(g['roles']))[:40]}\n")
    print(f'下料清单: {len(groups)} 种 -> demo/cut_list.csv')

    # ---- SCAD (裁后坐标) ----
    def sv(p): return f"[{p[0]:.0f}, {p[1]:.0f}, {p[2]:.0f}]"
    def col(m):
        mid = m['mid']
        for pre, c in (('LEG', 'ForestGreen'), ('BR', 'DarkOrange'), ('VG', 'DarkOrange'),
                       ('XB', 'DarkOrange'), ('DIA', 'SteelBlue'), ('L1', 'Crimson'),
                       ('L2', 'MediumOrchid'), ('L3', 'DeepPink')):
            if mid.startswith(pre): return c
        return 'Gray'
    out = [f'// SZK31102A 拆件模型 v1 (gap={gap}mm, 件号匹配 {n_ok}/{len(ms)})',
           f'// 未匹配件号杆件为灰色加粗可辨', '$fn=24;', '',
           'module tube(p1,p2,r,col){v=p2-p1;L=norm(v);ax=cross([0,0,1],v);translate(p1)color(col)if(norm(ax)<1e-9)rotate([0,v[2]>0?0:180,0])cylinder(h=L,r=r);else rotate(a=acos(min(1,max(-1,v[2]/L))),v=ax)cylinder(h=L,r=r);}', '']
    for m in ms:
        c = col(m)
        note = f"  //{m['piece_no']}" if m['piece_no'] else ''
        out.append(f'tube({sv(m["p1t"])},{sv(m["p2t"])},{m["r_mm"]:.0f},"{c}");{note}')
    open('demo/tower_frame_fab.scad', 'w', encoding='utf-8').write('\n'.join(out))

    # ---- 目检图: 原轴线(灰) vs 裁后(红), L1 头部放大 ----
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 8))
    for m in ms:
        a1.plot([m['p1'][0], m['p2'][0]], [m['p1'][2], m['p2'][2]], color='lightgray', lw=0.8)
        a1.plot([m['p1t'][0], m['p2t'][0]], [m['p1t'][2], m['p2t'][2]], color='crimson', lw=0.8)
    a1.set_title(f'full (gray=axis, red=cut gap={gap}mm)')
    a1.set_aspect('equal')
    for m in ms:
        zc = (m['p1'][2] + m['p2'][2]) / 2
        if not (128000 < zc < 136000): continue
        a2.plot([m['p1'][0], m['p2'][0]], [m['p1'][2], m['p2'][2]], color='lightgray', lw=1.0)
        a2.plot([m['p1t'][0], m['p2t'][0]], [m['p1t'][2], m['p2t'][2]], color='crimson', lw=1.0)
    a2.set_title('L1 head zoom'); a2.set_xlim(10000, 17500); a2.set_ylim(129500, 136500)
    a2.set_aspect('equal')
    plt.tight_layout(); plt.savefig('demo/fab_check.png', dpi=110)
    print('saved: demo/frame_fab.json, demo/cut_list.csv, demo/tower_frame_fab.scad, demo/fab_check.png')

if __name__ == '__main__':
    main()
