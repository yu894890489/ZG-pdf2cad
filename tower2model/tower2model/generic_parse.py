# -*- coding: utf-8 -*-
"""通用塔型解析建模: 任意塔型 001 正视图 -> 参数 -> members (LLM/VLM 协助)
策略: 拓扑/层数/腹杆形式信 VLM, 坐标数值尽量用矢量实测吸附精修。
四级兜底链保证任何情况都产出可用 members:
  1 llm              VLM JSON 可用
  2 llm_partial      VLM JSON 残缺, 程序补默认
  3 vector_only      VLM 失败/未配 LLM, 纯矢量近似
  4 fallback_default 矢量提取也失败, 默认锥形塔
结果仅供演示参考, meta.parse_mode/warnings 必须透传到报告
"""
import os, re, json, math, base64


# ---------------- A. 矢量提取 ----------------

def _filter_dim_lines(segs, diag):
    """剔除尺寸标注线。特征(用户确认 + 图面验证): 轴对齐线段, 端点带斜短 tick
    (尺寸起止符, ~45°), 且端点不与斜向塔身构件相连 —— 有 tick 只在一端的情况
    (尺寸链拼接段), 沿端点相连传播; 再删尺寸界线(一端接尺寸线一端悬空 /
    两端都接尺寸线, 且自身不连塔身)。返回 (保留 segs, 剔除数)"""
    def L(s): return math.hypot(s[1][0]-s[0][0], s[1][1]-s[0][1])
    def A(s): return math.degrees(math.atan2(abs(s[1][1]-s[0][1]), abs(s[1][0]-s[0][0])))
    tol = diag * 0.0015
    def mkgrid(points):
        g = {}
        for k, p in points:
            g.setdefault((int(p[0] // (tol*4)), int(p[1] // (tol*4))), []).append((k, p))
        return g
    def near_any(g, p, skip=None):
        cx, cy = int(p[0] // (tol*4)), int(p[1] // (tol*4))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for k, q in g.get((cx+dx, cy+dy), ()):
                    if k != skip and math.hypot(p[0]-q[0], p[1]-q[1]) <= tol:
                        return True
        return False
    ticks = mkgrid([(i, ((s[0][0]+s[1][0])/2, (s[0][1]+s[1][1])/2))
                    for i, s in enumerate(segs)
                    if 2.0 <= L(s) <= diag*0.015 and 20 <= A(s) <= 70])
    OBL = diag * 0.006  # 长斜线门槛: 塔身构件(腿/支撑)远长于 tick
    obl = mkgrid([(i, p) for i, s in enumerate(segs)
                  if L(s) >= OBL and 15 <= A(s) <= 75 for p in s])
    def axis(s):
        a = A(s)
        return a <= 3 or a >= 87
    # 候选: 轴对齐且至少一端带"干净 tick"(该端无长斜线锚定)。
    # 尺寸线可锚在塔身上(如 11380 根开线一端落在塔脚), 只看 tick 端是否干净
    cand = []
    seed = set()
    for i, s in enumerate(segs):
        if not axis(s) or L(s) < diag * 0.007:
            continue
        clean = [near_any(ticks, p) and not near_any(obl, p) for p in s]
        anchored = [near_any(obl, p) for p in s]
        if any(clean):
            cand.append(i)
            # 种子: 某 clean tick 端的另一端无锚定(悬空尺寸链), 或两端都干净
            if (clean[0] and not anchored[1]) or (clean[1] and not anchored[0]) \
                    or (clean[0] and clean[1]):
                seed.add(i)
    dim = set(seed)
    cand_set = set(cand)
    # 尺寸线常按重叠共线小段绘制(如 11380 根开线 = 144-200/162-203/181-367 三段
    # 搭接), 端点传播会断链 -> 共线(同行/同列 ±2pt)且间隔 <=15pt 也算相连
    def collinear_dim(i):
        s = segs[i]
        for j in dim:
            t = segs[j]
            horiz = abs(s[0][1]-s[1][1]) <= 2 and abs(t[0][1]-t[1][1]) <= 2 \
                and abs(s[0][1]-t[0][1]) <= 2
            vert = abs(s[0][0]-s[1][0]) <= 2 and abs(t[0][0]-t[1][0]) <= 2 \
                and abs(s[0][0]-t[0][0]) <= 2
            if not (horiz or vert):
                continue
            if horiz:
                a0, a1 = sorted((s[0][0], s[1][0]))
                b0, b1 = sorted((t[0][0], t[1][0]))
            else:
                a0, a1 = sorted((s[0][1], s[1][1]))
                b0, b1 = sorted((t[0][1], t[1][1]))
            if a0 <= b1 + 15 and b0 <= a1 + 15:
                return True
        return False
    while True:
        dpts = mkgrid([(i, p) for i in dim for p in segs[i]])
        grow = {i for i in cand if i not in dim
                and (near_any(dpts, segs[i][0]) or near_any(dpts, segs[i][1]))}
        grow |= {i for i in cand if i not in dim and collinear_dim(i)}
        if not grow:
            break
        dim |= grow
    # 尺寸界线: 轴对齐非塔身线段, 两端接尺寸线, 或一端接尺寸线另一端悬空
    allpts = mkgrid([(i, p) for i, s in enumerate(segs) for p in s])
    dpts = mkgrid([(i, p) for i in dim for p in segs[i]])
    out, n_dim = [], 0
    for i, s in enumerate(segs):
        if i in dim:
            n_dim += 1
            continue
        if i in cand_set:
            h0, h1 = near_any(dpts, s[0]), near_any(dpts, s[1])
            if (h0 and h1) or ((h0 or h1)
                               and not near_any(allpts, s[1] if h0 else s[0], i)):
                n_dim += 1
                continue
        out.append(s)
    return out, n_dim


def extract_segments(pdf_path):
    """001 PDF -> (segs_z_up[(x0,z0,x1,z1)] pt坐标, page(W,H) pt)。只保留视图区线段"""
    import fitz
    doc = fitz.open(pdf_path)
    page = doc[0]
    W, H = page.rect.width, page.rect.height
    diag = math.hypot(W, H)
    segs = []
    for d in page.get_drawings():
        if d.get('fill') is not None and d.get('color') is None:
            continue  # 纯填充面(文字轮廓底色等)
        for it in d['items']:
            if it[0] == 'l':
                segs.append(((it[1].x, it[1].y), (it[2].x, it[2].y)))
            elif it[0] == 're':
                r = it[1]
                segs += [((r.x0, r.y0), (r.x1, r.y0)), ((r.x1, r.y0), (r.x1, r.y1)),
                         ((r.x1, r.y1), (r.x0, r.y1)), ((r.x0, r.y1), (r.x0, r.y0))]
    if not segs:
        return [], (W, H)
    # 剔除贴页边的图框线(真实工程图有图框, 否则整页连成一簇)
    m = diag * 0.015
    segs = [s for s in segs
            if min(s[0][0], s[1][0]) > m and max(s[0][0], s[1][0]) < W - m
            and min(s[0][1], s[1][1]) > m and max(s[0][1], s[1][1]) < H - m]
    if not segs:
        return [], (W, H)
    # 剔除尺寸标注线(头尾带 45° tick 且不连塔身): 必须在长度过滤前,
    # tick 本身只有 ~6pt, 先过滤长度就把证据删了
    segs, n_dim = _filter_dim_lines(segs, diag)
    segs = [s for s in segs if math.hypot(s[1][0]-s[0][0], s[1][1]-s[0][1]) > diag*0.005]
    if not segs:
        return [], (W, H)
    # 端点网格并查集聚类, 取最高(z向最长)的簇为视图区(排除图框/明细表)
    tol = max(W, H) * 0.02
    parent = list(range(len(segs)))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb
    grid = {}
    for i, (p, q) in enumerate(segs):
        for (x, y) in (p, q):
            grid.setdefault((int(x//tol), int(y//tol)), []).append((i, x, y))
    for (cx, cy), cells in grid.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                other = grid.get((cx+dx, cy+dy))
                if not other: continue
                for a, x1_, y1_ in cells:
                    for b, x2_, y2_ in other:
                        if a != b and math.hypot(x1_-x2_, y1_-y2_) <= tol:
                            union(a, b)
    groups = {}
    for i in range(len(segs)):
        groups.setdefault(find(i), []).append(i)
    # 视图区特征: 含斜线(塔身坡度/横担斜撑); 图框/表格区全是正交线
    def cluster_stat(g):
        xs0 = min(min(segs[i][0][0], segs[i][1][0]) for i in g)
        xs1 = max(max(segs[i][0][0], segs[i][1][0]) for i in g)
        ys0 = min(min(segs[i][0][1], segs[i][1][1]) for i in g)
        ys1 = max(max(segs[i][0][1], segs[i][1][1]) for i in g)
        diag_n = sum(1 for i in g
                     if abs(segs[i][1][0]-segs[i][0][0]) > 2.0
                     and abs(segs[i][1][1]-segs[i][0][1]) > 2.0)
        return (ys1 - ys0), diag_n, (xs0, ys0, xs1, ys1)
    best, best_key = None, None
    for g in groups.values():
        if len(g) < 5: continue
        h, dn, bb = cluster_stat(g)
        key = (dn >= 3, h)  # 优先含斜线的簇, 其内取竖向跨度最大
        if best_key is None or key > best_key:
            best, best_key = g, key
    if best is None:
        best = list(range(len(segs)))
    best = _split_x_valley(best, segs)
    out = []
    for i in best:
        (x0, y0), (x1, y1) = segs[i]
        out.append((x0, H-y0, x1, H-y1))  # z 向上
    return out, (W, H)


def _split_x_valley(group, segs):
    """簇内 x 直方图切分: 大簇常把正视图与相邻的断面图/表格连成一片,
    按 x 覆盖找低谷, 取(斜线数, 竖向跨度)最优的段 —— 正视图段斜线最多"""
    if len(group) < 8:
        return group
    xs0 = min(min(segs[i][0][0], segs[i][1][0]) for i in group)
    xs1 = max(max(segs[i][0][0], segs[i][1][0]) for i in group)
    if xs1 - xs0 < 10.0:
        return group
    nb = 48
    bins = [[] for _ in range(nb)]
    for i in group:
        cx = (segs[i][0][0] + segs[i][1][0]) / 2.0
        bins[min(int((cx - xs0) / (xs1 - xs0) * nb), nb - 1)].append(i)
    # 每列竖向跨度
    def seg_h(idx_list):
        if not idx_list:
            return 0.0
        ys0 = min(min(segs[i][0][1], segs[i][1][1]) for i in idx_list)
        ys1 = max(max(segs[i][0][1], segs[i][1][1]) for i in idx_list)
        return ys1 - ys0
    filled = [b for b in range(nb) if bins[b]]
    if len(filled) < 8:
        return group
    # 找覆盖率低谷切分: 计数 < 峰值*0.15 的连续列视为谷
    peak = max(len(bins[b]) for b in filled)
    cuts, in_valley = [], False
    for b in range(nb):
        low = len(bins[b]) < peak * 0.15
        if low and not in_valley:
            cuts.append([b, b]); in_valley = True
        elif low:
            cuts[-1][1] = b
        else:
            in_valley = False
    cuts = [c for c in cuts if c[0] > 0 and c[1] < nb - 1]  # 首尾不算谷
    if not cuts:
        return group
    # 按谷切分段, 取(斜线数, 竖向跨度)最大段
    bounds, prev = [], 0
    for c0, c1 in cuts:
        bounds.append((prev, c0)); prev = c1 + 1
    bounds.append((prev, nb - 1))
    best, best_key = None, None
    for b0, b1 in bounds:
        idx = [i for b in range(b0, b1 + 1) for i in bins[b]]
        if len(idx) < 5:
            continue
        dn = sum(1 for i in idx
                 if abs(segs[i][1][0]-segs[i][0][0]) > 2.0
                 and abs(segs[i][1][1]-segs[i][0][1]) > 2.0)
        key = (dn, seg_h(idx))
        if best_key is None or key > best_key:
            best, best_key = idx, key
    if not best:
        return group
    # 只保留选中段范围(含少量外溢, 横担悬臂可能跨谷)内的线段
    xs = [segs[i][0][0] for i in best] + [segs[i][1][0] for i in best]
    lo, hi = min(xs), max(xs)
    pad = (hi - lo) * 0.02
    # 守卫: 被切掉的部分若不构成独立视图(竖向跨度 < 簇的一半, 例如只是横担悬臂翼),
    # 说明谷在视图内部(横担上下只有塔身有内容) -> 不切, 整簇保留
    cl_ys0 = min(min(segs[i][0][1], segs[i][1][1]) for i in group)
    cl_ys1 = max(max(segs[i][0][1], segs[i][1][1]) for i in group)
    other = [i for i in group
             if not (lo - pad <= (segs[i][0][0] + segs[i][1][0]) / 2.0 <= hi + pad)]
    if other:
        o_ys1 = max(max(segs[i][0][1], segs[i][1][1]) for i in other)
        o_ys0 = min(min(segs[i][0][1], segs[i][1][1]) for i in other)
        if o_ys1 - o_ys0 < (cl_ys1 - cl_ys0) * 0.5:
            return group
    # 只保留与选中段范围相交的线段(相交而非中心在内: 横担悬出弦杆一端在塔身内,
    # 按中心判定会把悬出部分整个丢掉, 横担只剩残端)
    keep = [i for i in group
            if min(segs[i][0][0], segs[i][1][0]) <= hi + pad
            and max(segs[i][0][0], segs[i][1][0]) >= lo - pad]
    # 切分后剩太少线段视为失败(目的是去邻图, 不要求降竖向跨度)
    if len(keep) < len(group) * 0.4:
        return group
    return keep


def view_bbox(segs):
    xs = [s[0] for s in segs] + [s[2] for s in segs]
    zs = [s[1] for s in segs] + [s[3] for s in segs]
    return min(xs), min(zs), max(xs), max(zs)


# ---------------- B. 比例标定 ----------------

def raw_h_spans(pdf_path):
    """全页(所有线簇, 含视图区外的尺寸标注线)水平线 -> [(z_pt, 最大连续跨度pt)]
    长线在 PDF 里常被拆成共线小段, 按同 z 合并成最大连续跨度"""
    import fitz
    doc = fitz.open(pdf_path)
    page = doc[0]
    W, H = page.rect.width, page.rect.height
    bands = {}
    for d in page.get_drawings():
        if d.get('fill') is not None and d.get('color') is None:
            continue  # 文字轮廓等纯填充
        for it in d['items']:
            if it[0] == 'l' and abs(it[1].y - it[2].y) <= 1.0:
                a, b = sorted((it[1].x, it[2].x))
                if b - a >= 5.0:
                    bands.setdefault(round((H - it[1].y) / 2.0), []).append((a, b))
    out = []
    for k, ivs in bands.items():
        ivs.sort()
        s, e = ivs[0]
        best = e - s
        for a, b in ivs[1:]:
            if a <= e + 2.0:
                e = max(e, b)
            else:
                best = max(best, e - s); s, e = a, b
        out.append((k * 2.0, max(best, e - s)))
    return out


def calibrate(ocr_txt, bb, page_h, dpi, hors=None, root_pts=None):
    """OCR 尺寸数字 ÷ 矢量线长 -> (sc_mm_per_pt, height_mm, conf, method, cands)
    竖直尺寸数字贴视区左右 -> 塔高类(除以包围盒高); 仅剩宽度数字时匹配塔底附近
    水平线实长(比包围盒宽准: 包围盒被横担悬臂撑大)。token 必须是纯数字,
    排除图签 "SZT45000X" 之类型号里的数字污染。
    root_pts: 塔底根开线长(pt, 底部窄带内线段全跨度), 供根开自洽校验。"""
    x0, z0, x1, z1 = bb
    hgt = z1 - z0
    # 视区上下一定范围内的水平线 (z, 跨度pt): 宽度标注的匹配对象
    hors = [(z, L) for (z, L) in (hors or [])
            if z0 - 0.3 * hgt <= z <= z1 + 0.1 * hgt]
    side, below, near_base = [], [], []
    try:
        lines = open(ocr_txt, encoding='utf-8').read().splitlines()
    except OSError:
        lines = []
    for ln in lines:
        parts = ln.split(None, 3)
        if len(parts) < 4: continue
        try:
            yp, xp = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        zp = page_h - yp*72.0/dpi
        xp = xp*72.0/dpi
        for tok in parts[3].split():
            # isdecimal 而非 isdigit: '④'/'²' 的 isdigit 为 True 但 int() 抛 ValueError
            if not tok.isdecimal(): continue
            v = int(tok)
            if not (5000 <= v <= 300000): continue
            dist = abs(xp - x0) if xp < x0 else (abs(xp - x1) if xp > x1 else 0)
            if dist > 0 and dist <= 0.3 * hgt \
               and z0 - 0.1 * hgt <= zp <= z1 + 0.1 * hgt:
                side.append(v)
            elif zp <= z0 and x0 - 0.2 * (x1 - x0) <= xp <= x1 + 0.2 * (x1 - x0):
                below.append((v, zp))
            elif z0 - 0.05 * hgt <= zp <= z0 + 0.10 * hgt \
                    and x0 - 0.15 * (x1 - x0) <= xp <= x1 + 0.15 * (x1 - x0):
                # 底部标注带(含视区内底线正上方): 根开标注常画在底线上方
                near_base.append((v, zp))
    sc = None; conf = 'low'; method = 'assumed_30m'
    if side:
        v = max(side)
        sc = v / hgt
        conf = 'high' if len(side) >= 3 else 'medium'
        method = f'ocr_height_{v}'
    elif below:
        v, zp = max(below)
        cands = [L for (z, L) in hors
                 if abs(z - zp) <= 0.08 * hgt and L >= 0.2 * (x1 - x0)]
        sc = v / (sum(cands) / len(cands)) if cands else v / (x1 - x0)
        conf = 'medium' if cands else 'low'
        method = f'ocr_width_{v}' + ('_line' if cands else '')
    # 根开自洽校验: 高度标注若是"呼高"(地面->挂点, 转角塔/终端塔常见), 比塔全高小,
    # 换算出的底宽会明显小于图面底宽标注 -> 改用底宽标注重标(全高=图面竖跨 x sc)
    if sc is not None and root_pts:
        ws = [v for v, _ in below] + [v for v, _ in near_base]
        wr = max(ws) if ws else None
        if wr:
            implied = root_pts * sc
            if abs(implied - wr) / wr > 0.08:
                sc2 = wr / root_pts
                h2 = sc2 * hgt
                if 0.5 < sc2 / sc < 2.0 and 10000 <= h2 <= 200000:
                    sc, h, conf = sc2, h2, 'medium'
                    method = f'ocr_width_{wr}_rootcheck(高度标注疑似呼高)'
    if sc is not None:
        h = sc * hgt
        if 10000 <= h <= 200000:
            # 高度类大值候选(供 VLM 指认全高; 视区旁可能混入非高度标注如累计线)
            cands = sorted(set(v for v in side if v >= h * 0.5), reverse=True)[:6]
            return sc, h, conf, method, cands
    sc = 30000.0 / hgt  # 兜底: 假定塔高 30m
    return sc, 30000.0, 'low', 'assumed_30m', []


# ---------------- 视图渲染 + VLM ----------------

def render_view_png(pdf_path, bb, page_h, work_dir):
    """视图区渲染 PNG 给 VLM: 竖长塔图切上下两半并排(30px 重叠防切横担),
    再整体缩到长边<=2048px。返回 base64"""
    import fitz
    x0, z0, x1, z1 = bb
    doc = fitz.open(pdf_path)
    page = doc[0]
    W = page.rect.width
    # z-up -> fitz y-down
    # 边距: 四周裁进尺寸标注数字(竖排全高标注通常在左侧 30~40pt), 供 VLM 直接读数;
    # 不取过大以免把相邻侧视图/明细表裁进来误导 VLM
    mx = max((x1 - x0) * 0.2, 40.0)
    mz = (z1 - z0) * 0.12
    clip = fitz.Rect(max(0, x0-mx), max(0, page_h-z1-mz),
                     min(W, x1+mx), min(page.rect.height, page_h-z0+mz))
    pix = page.get_pixmap(dpi=150, clip=clip)
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
        w, h = img.size
        if h > w * 2.2:  # 竖长塔图: 切上下两半并排, 保住标注数字可读性
            ov = 30
            h2 = h // 2
            top = img.crop((0, 0, w, h2 + ov))
            bot = img.crop((0, h2 - ov, w, h))
            gap = 24
            canvas = Image.new('RGB', (w * 2 + gap, max(h2 + ov, h - h2 + ov) + 12), 'white')
            canvas.paste(top, (0, 6))
            canvas.paste(bot, (w + gap, 6))
            img = canvas
        s = 2048.0 / max(img.size)
        if s < 1:
            img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))),
                             Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        png = buf.getvalue()
    except ImportError:
        png = pix.tobytes('png')  # 无 PIL: 原始输出
    try:
        open(os.path.join(work_dir, '001_view.png'), 'wb').write(png)
    except OSError:
        pass
    return base64.b64encode(png).decode()


VLMTOP_PROMPT = '''你是输电铁塔结构工程师。这是铁塔 001 总装图正视图截图(竖长图已切成上下两半并排: 左半=塔的上部, 右半=塔的下部)。
程序已从图 OCR 出若干竖排高度标注候选 height_candidates_mm, 但不确定哪个是主视图塔全高。
请读图回答(全部是数字, 优先读图上标注, 不确定填 null, 不要编造):
- total_height_mm: 主视图塔全高(从 height_candidates_mm 里指认, 或给图上读到的值)
- root_half_width_mm: 塔脚根开标注的一半(图上常标全根开, 除以 2)
- crossarm_count: 图上凸出塔身的横担层数(含地线支架顶架)
- crossarm_z_mm: 各横担层底标高(数组, 优先读图上标注)
- diaphragm_count: 塔身横隔(横材层)大约层数
只输出 JSON: {{"total_height_mm": n, "root_half_width_mm": n, "crossarm_count": n,
  "crossarm_z_mm": [n, ...], "diaphragm_count": n}}'''


def ask_vlm_digits(llm, image_b64, hints):
    """VLM 小任务调用: 只指认数字级拓扑(输出极小, 复杂图实测 ~450s; 大 JSON 会 >890s 超时)"""
    hints['说明'] = '若 crossarm_count 难数, 给你看到的大致层数即可'
    prompt = VLMTOP_PROMPT + '\n参考: ' + json.dumps(hints, ensure_ascii=False)
    err = 'unknown'
    for attempt in (1, 2):
        try:
            r = llm.chat_json(prompt, image_b64=image_b64, temperature=0.0,
                              timeout=890,
                              system='你是输电铁塔结构工程师, 精读工程图并输出 JSON。')
            if isinstance(r, dict) and (_num(r.get('total_height_mm')) or r.get('crossarm_count')):
                return r
            err = '返回不可用'
        except Exception as e:
            err = f'{type(e).__name__}: {str(e)[:80]}'
        if attempt == 1:
            print(f'  [vlm] 第 1 次调用失败({err}), 重试...', flush=True)
    raise RuntimeError(err)


# ---------------- D. 校验 + 精修 ----------------

def _num(v, default=None):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else default


def validate_and_refine(P, ctx):
    """VLM params -> (rebuild params, repairs[], warnings[])。坏项修/删, 缺项填充"""
    repairs, warns = [], []
    height = ctx['height_mm']
    bb = ctx['bb']; sc = ctx['sc_mm_per_pt']
    x0, z0, x1, z1 = bb
    vec_h = (z1 - z0) * sc
    hz = ctx['h_clusters']  # [(z_mm, n, xmax_mm)]

    # VLM 高度与标定差 >15% -> 整体缩放对齐矢量; 标定低置信时以 VLM 高度重标;
    # 标定已经根开自洽修正(ctx['calib_fixed'])时不再缩放: VLM 读到的往往是呼高,
    # 缩放会把全高缩回呼高(KC22D 教训)
    vh = _num(P.get('total_height_mm'))
    scale_k = 1.0
    if vh and vh > 0 and not ctx.get('calib_fixed'):
        if ctx['calib_conf'] != 'low':
            if abs(vh - vec_h) / vec_h > 0.15:
                scale_k = vec_h / vh
                repairs.append(f'VLM 高度 {vh:.0f} 与矢量标定 {vec_h:.0f} 偏差>15%, 已整体缩放 x{scale_k:.3f}')
        else:
            scale_k = vh / calib_assumed_height(ctx)
            repairs.append(f'标定置信低, 采用 VLM 高度 {vh:.0f} 重标比例 x{scale_k:.3f}')
    S = lambda v: v * scale_k

    # body_profile
    prof = []
    for pt in (P.get('body_profile') or []):
        if isinstance(pt, (list, tuple)) and len(pt) == 2:
            z, w = _num(pt[0]), _num(pt[1])
            if z is None or w is None: continue
            prof.append((S(float(z)), S(float(w))))
    prof.sort()
    clean = []
    for z, w in prof:
        if w <= 0:
            repairs.append(f'轮廓点 z={z:.0f} 宽度非法已剔除'); continue
        if clean and z <= clean[-1][0]:
            repairs.append(f'轮廓点 z={z:.0f} 非单调已剔除'); continue
        clean.append((z, w))
    if clean:
        zmin = clean[0][0]
        clean = [(z - zmin, w) for z, w in clean]  # 塔底归零
        if len(clean) == 1:
            clean.append((clean[0][0] + 1000, clean[0][1] * 0.5))
    else:
        clean = [(0.0, S(3000.0)), (height, S(600.0))]
        repairs.append('轮廓缺失, 用默认直线锥')
    profile = clean
    top_z = profile[-1][0]
    h_at = lambda z: _interp(profile, max(0.0, min(z, top_z)))

    # diaphragm_z 吸附水平线簇
    dia = []
    for z in (P.get('diaphragm_z') or []):
        z = _num(z)
        if z is None: continue
        dia.append(S(float(z)))
    dia = _snap_z(dia, [c[0] for c in hz], top_z * 0.03)
    dia = sorted({round(z) for z in dia if 0 <= z <= top_z * 1.02})[:30]
    if not dia:
        dia = sorted({round(z) for z, n, xm in hz if z <= top_z})[:12] \
              or [round(top_z*i/4) for i in range(1, 4)]
        repairs.append('横隔标高缺失, 取水平线簇/均分')

    # panels
    panels = []
    for p in (P.get('panels') or []):
        if not isinstance(p, dict): continue
        a, b = _num(p.get('z0')), _num(p.get('z1'))
        t = p.get('type')
        if a is None or b is None or t not in ('diamond', 'X', 'single', 'K', 'none'):
            continue
        a, b = S(float(a)), S(float(b))
        if b < a: a, b = b, a
        if b - a < top_z * 0.01: continue
        panels.append({'z0': a, 'z1': min(b, top_z), 'type': t})
    panels.sort(key=lambda p: p['z0'])
    if not panels:
        n = 4
        panels = [{'z0': top_z*i/n, 'z1': top_z*(i+1)/n, 'type': 'X'} for i in range(n)]
        repairs.append('腹杆节间缺失, 均分 4 段 X 型')

    # crossarms
    arms = []
    for ca in (P.get('crossarms') or [])[:8]:
        if not isinstance(ca, dict): continue
        zb = _num(ca.get('z_bottom'))
        if zb is None: continue
        zb = S(float(zb))
        top = [(S(float(x)), S(float(z))) for x, z in (ca.get('top_pts') or [])
               if isinstance(x, (int, float)) and isinstance(z, (int, float))]
        bot = [(S(float(x)), S(float(z))) for x, z in (ca.get('bot_pts') or [])
               if isinstance(x, (int, float)) and isinstance(z, (int, float))]
        hr = _num(ca.get('half_width_root'), 600.0)
        ht = _num(ca.get('half_width_tip'), 300.0)
        if not bot:  # 只有底标高 -> 矩形桁架近似
            body_w = h_at(zb)
            tip = body_w * 1.8
            h_arm = 1500.0
            bot = [(body_w*0.6, zb), (tip, zb)]
            top = [(body_w*0.6, zb+h_arm), (tip, zb+h_arm*0.7)]
            warns.append(f'横担 z={zb:.0f} 缺弦杆点表, 矩形近似')
        bot.sort(); top.sort()
        tip_x = max(bot[-1][0], top[-1][0] if top else 0)
        if tip_x <= h_at(zb) * 1.05:
            warns.append(f'横担 z={zb:.0f} 未凸出塔身, 已丢弃')
            continue
        if not top:
            h_arm = 1500.0
            top = [(bot[0][0], bot[0][1]+h_arm), (tip_x, bot[-1][1]+h_arm*0.7)]
        arms.append({'tag': f'L{len(arms)+1}', 'z_bottom': zb,
                     'top_pts': top, 'bot_pts': bot,
                     'half_root': float(hr), 'half_tip': float(ht),
                     'r_chord': 90.0, 'r_web': 55.0})
    if not arms:
        bh = h_at(top_z*0.9)
        arms = [{'tag': 'L1', 'z_bottom': top_z*0.9,
                 'top_pts': [(bh*0.6, top_z*0.9+1500), (bh*2.2, top_z*0.9+1200)],
                 'bot_pts': [(bh*0.6, top_z*0.9), (bh*2.2, top_z*0.9)],
                 'half_root': 600.0, 'half_tip': 300.0, 'r_chord': 90.0, 'r_web': 55.0}]
        repairs.append('横担缺失, 顶部默认地线横担')

    params = {
        'tower': str(P.get('tower_type') or 'UNKNOWN'),
        'height_mm': top_z,
        'root_half_mm': profile[0][1],
        'note': f'通用解析建模 (parse 待定): VLM 读图 + 矢量精修. {P.get("notes") or ""}'.strip(),
        'body_profile': profile,
        'diaphragm_z': [float(z) for z in dia],
        'panels': panels,
        'vg_top': None,
        'crossarms': arms,
    }
    return params, repairs, warns


def _interp(profile, z):
    for (z0, w0), (z1, w1) in zip(profile, profile[1:]):
        if z0 <= z <= z1:
            return w0 + (w1-w0)*(z-z0)/(z1-z0) if z1 > z0 else w0
    return profile[-1][1]


def _snap_z(zs, targets, tol):
    out = []
    for z in zs:
        if targets:
            near = min(targets, key=lambda t: abs(t-z))
            if abs(near - z) <= tol:
                z = near
        out.append(z)
    return out


# ---------------- 矢量兜底 (level 3/4) ----------------

def calib_assumed_height(ctx):
    """标定低置信时假定的高度(mm)——与 calibrate 兜底一致"""
    return 30000.0


def h_line_clusters(segs, bb):
    """水平长线 z 聚簇 -> [[z, n, xmax]]"""
    x0, z0, x1, z1 = bb
    hgt = z1 - z0
    zs = []
    for s in segs:
        if abs(s[3]-s[1]) < hgt*0.002:
            ln = abs(s[2]-s[0])
            if ln > (x1-x0)*0.08:
                zs.append(((s[1]+s[3])/2, ln, max(s[0], s[2])))
    zs.sort()
    out = []
    for z, ln, xm in zs:
        if out and abs(out[-1][0] - z) < hgt*0.01:
            out[-1][1] += 1
            out[-1][2] = max(out[-1][2], xm)
        else:
            out.append([z, 1, xm])
    return out


def _raw_arm_bands(segs, bb, sc):
    """横担/塔头矢量直通: 悬出塔身的线段按 z 聚带(参数化梯形近似不出真实
    塔头形状——斜放地线顶架/三角导线横担, 图面线段原样搬进模型才保形)。
    返回 [{'z_bottom','z_top','raw_segs':[x0,z0,x1,z1]}] (mm, x 相对轴心, z 相对塔底)"""
    x0, z0, x1, z1 = bb
    hgt = z1 - z0
    def band_x(f0, f1):
        xs = []
        for s in segs:
            for x, z in ((s[0], s[1]), (s[2], s[3])):
                if z0 + hgt * f0 <= z <= z0 + hgt * f1:
                    xs.append(x)
        return xs
    bx = band_x(0.0, 0.06)
    axis = (min(bx) + max(bx)) / 2.0 if bx else (x0 + x1) / 2.0
    # 逐层宽度包络 w(z): 每层取跨越该层的线段的最大 |x-axis|
    lv = int(hgt * 2)
    w = [0.0] * lv
    for s in segs:
        lo, hi = min(s[1], s[3]) - z0, max(s[1], s[3]) - z0
        mx = max(abs(s[0] - axis), abs(s[2] - axis))
        for k in range(max(0, int(lo / hgt * lv)), min(lv, int(hi / hgt * lv) + 1)):
            if mx > w[k]:
                w[k] = mx
    upper = w[int(lv * 0.5):]
    med = sorted(upper)[len(upper) // 2] if upper else 0.0
    thr = 1.5 * med
    if thr <= 0:
        return []
    # 连续 w>thr 的层为带, 向外扩到 w>0.7thr(横担根部宽度回落)
    GAP = max(1, int(0.02 * lv))
    bands = []
    k = int(lv * 0.45)
    while k < lv:
        if w[k] > thr:
            lo = hi = k
            j = k
            while j < lv and (w[j] > thr or (w[j] > 0.7 * thr and j - hi <= GAP)):
                if w[j] > thr:
                    hi = j
                j += 1
            bands.append([lo, hi])
            k = j + GAP
        else:
            k += 1
    # 相邻带间隙 < 0.045*hgt 合并(横担上下弦之间腹部宽度回落会把一层拆成两带)
    merged = []
    for b in bands:
        if merged and b[0] - merged[-1][1] < 0.045 * lv:
            merged[-1][1] = b[1]
        else:
            merged.append(b)
    bands = merged
    out = []
    for lo, hi in bands:
        zb, zt = z0 + lo / lv * hgt, z0 + (hi + 1) / lv * hgt
        ext = zt - zb
        if ext > 0.3 * hgt:
            continue
        raw = []
        # 塔身半宽 = 带"正下方"紧邻层的宽度包络(带边缘层常正好落在横担
        # 弦杆上, 包络=横担半宽会把门槛抬到没收腹杆; 带下方才是塔身处);
        # 只收真正悬出塔身的线段, 塔身 K 撑/斜材不进横担
        kb = max(0, lo - max(2, int(0.008 * lv)))
        wmin = w[kb]
        for s in segs:
            zc = (s[1] + s[3]) / 2
            mx = max(abs(s[0] - axis), abs(s[2] - axis))
            zext = abs(s[3] - s[1])
            if zb - 0.015 * hgt <= zc <= zt + 0.015 * hgt \
                    and mx > 1.05 * wmin and zext < max(0.15 * hgt, 1.3 * ext):
                raw.append(s)
        if len(raw) >= 4:
            raw.sort(key=lambda s: -math.hypot(s[2] - s[0], s[3] - s[1]))
            out.append({'z_bottom': (zb - z0) * sc, 'z_top': (zt - z0) * sc,
                        'raw_segs': [((s[0] - axis) * sc, (s[1] - z0) * sc,
                                      (s[2] - axis) * sc, (s[3] - z0) * sc)
                                     for s in raw[:120]]})
    return out


def attach_raw_arms(params, segs, bb, sc):
    """把图面横担/塔头矢量带写进 params['crossarms'](llm/vector 模式通用)。
    返回 (带数, 线段数); 无带不动 params"""
    bands = _raw_arm_bands(segs, bb, sc)
    if not bands:
        return 0, 0
    params['crossarms'] = [
        {'tag': f'L{i+1}', 'z_bottom': b['z_bottom'], 'raw_segs': b['raw_segs'],
         'half_root': 700.0, 'half_tip': 500.0, 'r_chord': 90.0, 'r_web': 55.0}
        for i, b in enumerate(bands)]
    return len(bands), sum(len(b['raw_segs']) for b in bands)


def vector_params(segs, bb, sc, height):
    """纯矢量近似轮廓/横隔/横担 (level 3)"""
    x0, z0, x1, z1 = bb
    hgt = z1 - z0
    zmin = z0
    prof_z = [(z - zmin) * sc for z in (z0, z1)]
    # 轴心取塔底带中心(非 bbox 中心): 横担悬臂常单侧凸出, bbox 中心会偏,
    # 轴心一偏所有 |x-axis| 半宽全错(KC22D 教训)
    def band_x(frac0, frac1):
        xs = []
        for s in segs:
            for x, z in ((s[0], s[1]), (s[2], s[3])):
                if z0 + hgt*frac0 <= z <= z0 + hgt*frac1:
                    xs.append(x)
        return xs
    bx = band_x(0.0, 0.06)
    axis = (min(bx) + max(bx)) / 2.0 if bx else (x0 + x1) / 2.0
    def band_w(frac0, frac1):
        ws = [abs(x - axis) for x in band_x(frac0, frac1)]
        return max(ws) * sc if ws else 3000.0*sc*hgt/30000.0
    root_half = band_w(0.0, 0.08)
    # 塔顶半宽: 顶部带若被地线顶架/横担占住会严重高估 -> 只信主腿斜线
    # (跨高 >60% 的斜线段在 z1 处的插值 x); 没有斜线再退回带宽
    legs = [s for s in segs
            if abs(s[2] - s[0]) >= 2.0 and abs(s[3] - s[1]) >= 0.5 * hgt
            and min(s[1], s[3]) <= z0 + 0.1 * hgt]
    if legs:
        top_half = max(500.0, max(abs(s[0] + (s[2] - s[0]) * (z1 - s[1]) / (s[3] - s[1])
                                  - axis) for s in legs) * sc)
    else:
        top_half = max(500.0, band_w(0.92, 1.0) * 0.35)
    height_mm = hgt * sc
    profile = [(0.0, root_half), (height_mm, top_half)]
    hz = h_line_clusters(segs, bb)
    dia = sorted({round((z - zmin)*sc) for z, n, xm in hz if z - zmin > hgt*0.05})[:12]
    panels = [{'z0': height_mm*i/4, 'z1': height_mm*(i+1)/4, 'type': 'X'} for i in range(4)]
    arms = []
    for z, n, xm in hz:
        zm = (z - zmin) * sc
        if zm < height_mm*0.5 or len(arms) >= 3: continue
        bw = _interp(profile, zm)
        tip = (xm - axis) * sc
        if tip > bw * 1.4 and tip > 0:
            arms.append({'tag': f'L{len(arms)+1}', 'z_bottom': zm,
                         'top_pts': [(bw*0.6, zm+1200), (tip, zm+900)],
                         'bot_pts': [(bw*0.6, zm), (tip, zm)],
                         'half_root': 600.0, 'half_tip': 300.0,
                         'r_chord': 90.0, 'r_web': 55.0})
    return {
        'tower': 'UNKNOWN', 'height_mm': height_mm, 'root_half_mm': root_half,
        'note': '通用解析建模: 纯矢量近似(VLM 不可用)',
        'body_profile': profile,
        'diaphragm_z': [float(z) for z in dia] or [height_mm*i/4 for i in range(1, 4)],
        'panels': panels, 'vg_top': None, 'crossarms': arms,
    }


DEFAULT_PARAMS = {
    'tower': 'UNKNOWN', 'height_mm': 30000.0, 'root_half_mm': 3000.0,
    'note': '通用解析建模: 全部兜底默认锥形塔(图纸不可解析)',
    'body_profile': [(0.0, 3000.0), (30000.0, 600.0)],
    'diaphragm_z': [7500.0, 15000.0, 22500.0],
    'panels': [{'z0': 0.0, 'z1': 15000.0, 'type': 'X'},
               {'z0': 15000.0, 'z1': 30000.0, 'type': 'X'}],
    'vg_top': None,
    'crossarms': [
        {'tag': 'L1', 'z_bottom': 24000.0,
         'top_pts': [(1800, 25500), (4200, 25200)], 'bot_pts': [(1800, 24000), (4200, 24000)],
         'half_root': 600.0, 'half_tip': 300.0, 'r_chord': 90.0, 'r_web': 55.0},
    ],
}


# ---------------- 对外入口 ----------------

def build_frame(pdf_001, ocr_txt, llm, work_dir, log, dpi=200):
    """永不抛异常。返回 rebuild params + meta(parse_mode/confidence/warnings)"""
    warnings = []
    segs, page = [], None
    try:
        segs, page = extract_segments(pdf_001)
    except Exception as e:
        warnings.append(f'矢量提取失败: {e}')
    bb = view_bbox(segs) if segs else (0.0, 0.0, 100.0, 400.0)

    calib = {'sc_mm_per_pt': None, 'height_mm': 30000.0, 'conf': 'low', 'method': 'assumed_30m',
             'cands': []}
    if segs:
        try:
            hors = raw_h_spans(pdf_001)
            # 塔底根开线长(pt): 底部 6% 带内线段的全 x 跨度(含腿部斜线足),
            # 供根开自洽校验(高度标注可能是"呼高"而非全高)
            hpt = bb[3] - bb[1]
            band = [s for s in segs
                    if s[1] >= bb[1] - 0.01 * hpt and s[3] <= bb[1] + 0.06 * hpt
                    and abs(s[2] - s[0]) >= 0.02 * hpt]
            root_pts = ((max(max(s[0], s[2]) for s in band)
                         - min(min(s[0], s[2]) for s in band)) if band else None)
            sc, h, conf, method, cands = calibrate(ocr_txt, bb, page[1], dpi, hors,
                                                   root_pts=root_pts)
            calib = {'sc_mm_per_pt': sc, 'height_mm': h, 'conf': conf, 'method': method,
                     'cands': cands, 'fixed': 'rootcheck' in method}
            log(f'  标定: {h:.0f}mm (sc={sc:.2f}mm/pt, {conf}, {method})')
            if calib['fixed']:
                log(f'  ⚠ 根开自洽校验触发: 底宽标注与高度标注矛盾, 已按底宽重标'
                    f'(全高={h:.0f}mm 为图面竖跨换算值)')
            if len(cands) > 1 and cands[0] / cands[1] > 1.2:
                log(f'  ⚠ 高度候选有分歧 {cands}, 交由 VLM 指认')
        except Exception as e:
            warnings.append(f'比例标定失败: {e}')
        if calib['sc_mm_per_pt'] is None and segs:
            # 标定异常兜底: 按假定塔高 30m 换算, 后续照常走矢量/VLM 流程
            calib['sc_mm_per_pt'] = 30000.0 / max(1.0, bb[3] - bb[1])
            w = warnings[-1] if warnings else ''
            log(f'  标定失败({w}), 按 30m 假定塔高兜底 sc={calib["sc_mm_per_pt"]:.2f}')
    hz = h_line_clusters(segs, bb) if segs else []
    ctx = {'bb': bb, 'height_mm': calib['height_mm'], 'sc_mm_per_pt': calib['sc_mm_per_pt'],
           'calib_conf': calib['conf'], 'calib_fixed': bool(calib.get('fixed')),
           'h_clusters': [(z*calib['sc_mm_per_pt'], n, xm*calib['sc_mm_per_pt'])
                          for z, n, xm in hz] if segs else []}

    params, parse_mode, confidence = None, None, {}
    # 级别 1/2: VLM 指认(小任务: 只出数字, 几何由矢量生成 —— 拓扑信 VLM, 数值信矢量)
    if llm is not None and segs:
        try:
            img = render_view_png(pdf_001, bb, page[1], work_dir)
            hints = {'scale_mm_per_pt': round(calib['sc_mm_per_pt'], 3),
                     'estimated_height_mm': round(calib['height_mm']),
                     'height_candidates_mm': calib['cands'],
                     'view_width_mm': round((bb[2]-bb[0])*calib['sc_mm_per_pt']),
                     'horizontal_levels_mm': [round(z) for z, n, xm in ctx['h_clusters'][:15]]}
            log('  VLM 读图中(复杂图实测 5~15 分钟)...')
            D = ask_vlm_digits(llm, img, hints)
            try:
                json.dump(D, open(os.path.join(work_dir, 'vlm_params.json'), 'w', encoding='utf-8'),
                          ensure_ascii=False, indent=1)
            except OSError:
                pass
            if isinstance(D, dict) and (D.get('body_profile') or _num(D.get('total_height_mm'))
                                        or D.get('crossarm_count') is not None):
                if D.get('body_profile'):  # 完整 schema(测试注入): 直接用
                    P = D
                else:                      # 数字级 schema -> 程序组装几何
                    # VLM 指认全高 -> 匹配高度候选重定比例(数值仍信矢量);
                    # 标定已经根开自洽修正(fixed)时跳过: VLM 读到的往往就是呼高,
                    # 再缩放会把全高缩回呼高(KC22D 教训)
                    vh = _num(D.get('total_height_mm'))
                    if vh and calib['cands'] and not calib.get('fixed'):
                        match = [c for c in calib['cands'] if abs(c - vh) / c <= 0.03]
                        if match and abs(match[0] - calib['height_mm']) > 1.0:
                            sc2 = match[0] / (bb[3] - bb[1])
                            ctx['sc_mm_per_pt'] = sc2
                            ctx['height_mm'] = match[0]
                            ctx['h_clusters'] = [(z*sc2, n, xm*sc2) for z, n, xm in hz]
                            calib['height_mm'] = match[0]
                            calib['sc_mm_per_pt'] = sc2
                            calib['method'] += f'->vlm_confirm_{match[0]}'
                            log(f'  VLM 指认全高 {match[0]:.0f}mm, 重新标定 sc={sc2:.2f}mm/pt')
                    # 横担层: VLM 给了标高就吸附水平线簇, 否则按层数取上部凸出层
                    hz_mm = ctx['h_clusters']
                    tol = 0.03 * ctx['height_mm']
                    zs = []
                    for v in (D.get('crossarm_z_mm') or []):
                        z = _num(v)
                        if z is None:
                            continue
                        near = [zm for zm, n, xm in hz_mm if zm > ctx['height_mm']*0.5
                                and abs(zm - z) <= tol]
                        zs.append(min(near, key=lambda t: abs(t - z)) if near else z)
                    if not zs:
                        n = int(_num(D.get('crossarm_count')) or 2)
                        upper = sorted([t for t in hz_mm if t[0] > ctx['height_mm'] * 0.5],
                                       key=lambda t: -t[0])
                        zs = [t[0] for t in upper[:n]]
                    P = {'tower_type': D.get('tower_type'),
                         'total_height_mm': ctx['height_mm'],
                         'root_half_width_mm': _num(D.get('root_half_width_mm')),
                         'body_profile': None,
                         'diaphragm_z': None,
                         'panels': None,
                         'crossarms': [{'name': f'L{i+1}', 'z_bottom': z} for i, z in
                                       enumerate(sorted(set(round(z) for z in zs)))]}
                params, repairs, warns = validate_and_refine(P, ctx)
                warnings += repairs + warns
                parse_mode = 'llm'
                confidence = {'scale': 'high' if 'vlm_confirm' in calib['method'] else calib['conf'],
                              'body': 'low(矢量两点锥)', 'crossarms': 'medium(矢量水平线)'}
                log(f'  VLM 指认完成: 全高 {calib["height_mm"]:.0f}mm, '
                    f'横担 {len(params["crossarms"])} 层')
            else:
                warnings.append('VLM 返回不可用, 降级纯矢量')
        except Exception as e:
            warnings.append(f'VLM 调用失败: {e}')
    elif llm is None:
        warnings.append('LLM 未配置, 纯矢量解析')
    # 级别 3: 纯矢量
    if params is None:
        if segs:
            try:
                params = vector_params(segs, bb, calib['sc_mm_per_pt'], calib['height_mm'])
                parse_mode = 'vector_only'
            except Exception as e:
                warnings.append(f'矢量近似失败: {e}')
        # 级别 4: 默认
        if params is None:
            params = dict(DEFAULT_PARAMS)
            parse_mode = 'fallback_default'

    from . import rebuild
    # 塔头/横担矢量直通(llm/vector 通用): 图面桁架线段原样进模, 保真实形状
    if segs and params is not None and parse_mode != 'fallback_default':
        try:
            nb, nseg = attach_raw_arms(params, segs, bb, calib['sc_mm_per_pt'])
            if nb:
                log(f'  横担/塔头矢量直通: {nb} 带 {nseg} 段(保留图面真实桁架形状)')
        except Exception as e:
            warnings.append(f'横担矢量直通失败: {e}')
    frame = rebuild.build_frame_from_params(params)
    frame['meta']['parse_mode'] = parse_mode
    frame['meta']['confidence'] = confidence
    frame['meta']['warnings'] = warnings
    frame['meta']['parse_method'] = calib['method']
    if parse_mode != 'llm':
        frame['meta']['spec_level'] = '不可靠: 通用解析, 规格为估算'
    log(f'  解析完成: mode={parse_mode}, {len(frame["members"])} 杆, '
        f'高 {frame["meta"]["height_mm"]/1000:.1f}m')
    for w in warnings:
        log(f'  ⚠ {w}')
    return frame
