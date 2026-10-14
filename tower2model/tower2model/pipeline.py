# -*- coding: utf-8 -*-
"""主流水线: inputs(图纸PDF[+001.dxf]) -> outputs(模型/下料/三视图/审查报告)
阶段:
  S1 OCR 明细表(可缓存跳过)  S1.5 塔型识别分流  S2 行解析(可选 LLM 清洗)
  S3 重建(builtin 内置参数表 / generic VLM+矢量解析)  S4 规格挂接 + BOM
  S5 拆件留缝 + 件号匹配      S6 碰撞检查
  S7 渲染: 三视图 + OpenSCAD 真实感  S8 检查汇总 + 报告(可选 LLM 润色)
"""
import os, sys, json, re, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from . import ocr as ocr_mod
from . import schedule as sch_mod
from . import rebuild, specs, fabricate, checks, render, generic_parse
from .config import load_config, find_openscad
from .llm import LLM, clean_schedule_rows, review_report


# 内置参数化重建的塔型(rebuild._SZK31102A_PARAMS); 其他塔型走通用解析路径
SUPPORTED_TOWER = 'SZK31102A'
TOWER_RE = re.compile(r'SZ[A-Z]{0,3}\d{4,}[A-Z]?')


def detect_tower(sheet_pdfs, ocr_dir, log):
    """塔型识别: 型号取自 001 图签 OCR; 001 必需(正视图是几何唯一来源, 缺则报错)。
    返回 {'tower': 型号或'UNKNOWN', 'parse_mode': 'builtin'|'generic', 'foreign_sheets': []}"""
    if not sheet_pdfs:
        raise ValueError('没有可识别的图纸(文件名需以 -NNN.pdf 结尾, 如 37-SA36901S-T0121-004.pdf)')
    # 001 缺失, 或整卷导出命名(无 -NNN 后缀)时, 每轮强制重挑总装图:
    # OCR 含"总装/塔总图"且非目录的页优先; 强制重挑是为避免上轮拷贝的
    # ocr001.txt 残留内容(已非目录页)让本轮误判 001 指回第 1 页
    _ocr_cache = {}
    def ocr_txt(s):
        if s not in _ocr_cache:
            try:
                _ocr_cache[s] = open(os.path.join(ocr_dir, f'ocr{s}.txt'),
                                     encoding='utf-8').read()
            except OSError:
                _ocr_cache[s] = ''
        return _ocr_cache[s]
    legacy = any(re.search(r'-\d{3}\.pdf$', os.path.basename(p))
                 for p in sheet_pdfs.values())
    if '001' not in sheet_pdfs or not legacy:
        import shutil
        cand = [s for s in sorted(sheet_pdfs)
                if '目录' not in ocr_txt(s) and ('总装' in ocr_txt(s) or '总图' in ocr_txt(s))]
        pick = cand[0] if cand else min(sheet_pdfs)
        log(f'  ⚠ 无 001 总装图页号, 以第 {int(pick)} 页作为总装图来源'
            + ('(OCR 命中"总图/总装")' if cand else '(兜底: 最小页号, 请人工核对)'))
        sheet_pdfs['001'] = sheet_pdfs.pop(pick)
        src = os.path.join(ocr_dir, f'ocr{pick}.txt')
        dst = os.path.join(ocr_dir, 'ocr001.txt')
        if os.path.exists(src) and os.path.abspath(src) != os.path.abspath(dst):
            shutil.copy(src, dst)
    def tower_of(sheet):
        try:
            txt = open(os.path.join(ocr_dir, f'ocr{sheet}.txt'),
                       encoding='utf-8').read().replace(' ', '')
        except OSError:
            return None
        found = TOWER_RE.findall(txt)
        return max(set(found), key=found.count) if found else None
    tower = tower_of('001') or 'UNKNOWN'
    foreign = []
    if tower not in ('UNKNOWN',):
        for s in sorted(sheet_pdfs):
            t = tower_of(s)
            if t and t != tower:
                foreign.append(f'{s}({t})')
    mode = 'builtin' if tower == SUPPORTED_TOWER else 'generic'
    if mode == 'builtin':
        log(f'  塔型 {tower}(内置参数化重建), 含 001 总装图')
        if foreign:
            log(f'  ⚠ 混入其他塔型图纸: {", ".join(foreign)}(照常建模, 请人工核对)')
    else:
        log(f'  塔型 {tower}: 非内置塔型, 走通用解析建模(VLM + 矢量)')
        if foreign:
            log(f'  ⚠ 混入其他型号图纸: {", ".join(foreign)}')
    return {'tower': tower, 'parse_mode': mode, 'foreign_sheets': foreign}


def run(input_dir, out_dir, gap=None, dpi=None, sheets=None,
        ocr_cache=None, no_llm=False, cfg_path=None):
    t0 = time.time()
    cfg = load_config(cfg_path)
    gap = gap or cfg['gap_mm']
    dpi = dpi or cfg['ocr_dpi']
    os.makedirs(out_dir, exist_ok=True)
    work = os.path.join(out_dir, 'work')
    ocr_dir = os.path.join(work, 'ocr')
    os.makedirs(ocr_dir, exist_ok=True)
    log = lambda s: print(s, flush=True)

    # ---- S1 OCR (缓存优先) ----
    log(f'[S1] OCR 明细表 (dpi={dpi})')
    if ocr_cache:
        import shutil
        n = 0
        for f in os.listdir(ocr_cache):
            if f.startswith('ocr') and f.endswith('.txt'):
                shutil.copy(os.path.join(ocr_cache, f), ocr_dir); n += 1
        log(f'  缓存预热 {n} 个 OCR 结果')
    sheet_pdfs = ocr_mod.batch_ocr(input_dir, ocr_dir, sheets, dpi, cfg['ocr_tile'])

    # ---- S1.5 塔型识别分流 ----
    log('[S1.5] 塔型识别')
    detect = detect_tower(sheet_pdfs, ocr_dir, log)

    # ---- S2 行解析 (+可选 LLM 清洗) ----
    log('[S2] 明细表行解析')
    rows_by_sheet = sch_mod.parse_all(ocr_dir, dpi)
    n_rows = sum(len(v) for v in rows_by_sheet.values())
    log(f'  {len(rows_by_sheet)} 张图, {n_rows} 行')
    llm = None if no_llm else LLM.from_config(cfg)
    if llm:
        log(f'  [llm] {cfg["llm_model"]} @ {cfg["llm_api_base"]} 启用, 清洗 OCR 行')
        fixed_n = 0
        for s, rows in rows_by_sheet.items():
            # 表格锚定解析后行质量已高, 只洗校验未过行数多的图 (省 LLM 时延)
            nbad = sum(1 for r in rows if not r.get('chk', True))
            if nbad < 5: continue
            fx = clean_schedule_rows(llm, s, rows)
            if fx is not None:
                rows_by_sheet[s] = fx; fixed_n += 1
        log(f'  [llm] 清洗完成 {fixed_n} 张')
    else:
        log('  [llm] 未配置 (config.yaml llm_api_base), 跳过 LLM 清洗')
    rows_path = os.path.join(work, 'schedule_rows.json')
    json.dump(rows_by_sheet, open(rows_path, 'w', encoding='utf-8'), ensure_ascii=False)
    # 几何解析用 LLM(独立于 no_llm: no_llm 只跳过行清洗/报告润色, 通用路径的 VLM 读图是几何来源)
    llm_geo = LLM.from_config(cfg)

    # ---- S3 重建 ----
    if detect['parse_mode'] == 'builtin':
        log('[S3] 参数化重建 (001 基准 v3)')
        frame = rebuild.build_frame()
    else:
        log('[S3] 通用解析建模 (VLM 读图 + 矢量精修)')
        try:
            frame = generic_parse.build_frame(
                sheet_pdfs['001'], os.path.join(ocr_dir, 'ocr001.txt'),
                llm_geo, work, log, dpi)
        except Exception as e:
            log(f'  解析异常({e}), 默认锥形塔兜底')
            frame = rebuild.build_frame_from_params(dict(generic_parse.DEFAULT_PARAMS))
            frame['meta']['parse_mode'] = 'fallback_default'
            frame['meta']['warnings'] = [f'解析异常: {e}']
    frame_path = os.path.join(out_dir, 'frame.json')
    json.dump(frame, open(frame_path, 'w', encoding='utf-8'), ensure_ascii=False)
    with open(os.path.join(out_dir, 'tower_frame.scad'), 'w', encoding='utf-8') as f:
        f.write(rebuild.to_scad(frame))
    log(f'  {len(frame["members"])} 杆')

    # ---- S4 规格 ----
    log('[S4] 规格挂接')
    if detect['parse_mode'] == 'builtin':
        n_att = specs.attach(frame)
    else:
        n_att = specs.attach_generic(frame, rows_path)
    log(f'  挂重 {n_att}')

    # ---- S5 拆件 ----
    log(f'[S5] 拆件留缝 (gap={gap}mm) + 件号匹配')
    ms = fabricate.apply_gaps(frame['members'], gap)
    for m in ms:
        m['len_mm'] = m['cut_len_mm']
    rows = fabricate.load_rows([rows_path])
    n_ok = fabricate.match_pieces(ms, rows)
    n_drawing = sum(1 for m in ms if m.get('spec_src') == '图纸明细表')
    log(f'  件号 {n_ok}/{len(ms)}, 规格取图纸 {n_drawing}, 行池 {len(rows)}')

    # ---- S5b BOM (件号化, 在匹配后汇总) ----
    bom_rows, total_w = specs.write_bom(frame, os.path.join(out_dir, 'bom.csv'), members=ms)
    log(f'  总重 {total_w/1000:.1f} t, BOM {len(bom_rows)} 行 -> bom.csv')
    frame_fab = {'meta': dict(frame['meta'], gap_mm=gap,
                              fab_level='拆件: 端头回退留缝 + 明细表件号匹配'),
                 'members': ms}
    fab_path = os.path.join(out_dir, 'frame_fab.json')
    json.dump(frame_fab, open(fab_path, 'w', encoding='utf-8'), ensure_ascii=False)
    n_kinds = fabricate.write_cut_list(ms, os.path.join(out_dir, 'cut_list.csv'))
    log(f'  下料清单 {n_kinds} 种 -> cut_list.csv')

    # ---- S6 碰撞 ----
    log('[S6] 碰撞检查')
    col = checks.collision_check(frame['members'])
    with open(os.path.join(out_dir, 'collision_report.txt'), 'w', encoding='utf-8') as f:
        f.write(f"碰撞检查 (clearance=10mm): 碰撞 {len(col['collisions'])}, "
                f"X撑交叉 {col['xcross']}, 节点区接触 {col['joint']}\n")
        for a, b, d in col['collisions'][:50]:
            f.write(f'{a} x {b} dist={d}\n')
    log(f"  碰撞 {len(col['collisions'])}, X撑交叉 {col['xcross']}")

    # ---- S7 渲染 ----
    log('[S7] 渲染三视图 + STL + OpenSCAD')
    tv = render.three_views(frame_fab, os.path.join(out_dir, 'views_三视图.png'),
                            f'{frame["meta"]["tower"]} gap={gap}mm')
    n_tri, stl_path = render.write_stl(frame_fab, os.path.join(out_dir, 'tower_frame_real.stl'))
    log(f'  STL 实体 {n_tri} 面 ({os.path.getsize(stl_path)/1e6:.1f} MB)')
    scad_real = os.path.join(out_dir, 'tower_frame_real.scad')
    with open(scad_real, 'w', encoding='utf-8') as f:
        f.write(render.real_scad(frame_fab))
    exe = find_openscad(cfg)
    scad_pngs = []
    if exe:
        views = render.views_for(frame_fab, frame["meta"].get("tower"))
        for v in ('iso', 'head', 'joint'):
            p = os.path.join(out_dir, f'render_{v}.png')
            try:
                if render.openscad_png(scad_real, p, views[v], exe):
                    scad_pngs.append(p)
            except Exception as e:
                log(f'  openscad {v} 失败: {e}')
        log(f'  三视图 + OpenSCAD {len(scad_pngs)} 张 (exe={exe})')
    else:
        log('  三视图完成; OpenSCAD 未找到(打包目录 vendor/openscad 或本机安装), 跳过真实感渲染')

    # ---- S8 检查 + 报告 ----
    log('[S8] 检查汇总 + 报告')
    stats, findings = checks.run_checks(frame_fab, col)
    pm = frame['meta'].get('parse_mode', 'builtin')
    stats['parse_mode'] = pm
    stats['tower'] = frame['meta']['tower']
    stats['spec_drawing'] = sum(1 for m in frame_fab['members'] if m.get('spec_src') == '图纸明细表')
    report = [f'# {frame["meta"]["tower"]} 建模审查报告', '']
    if pm != 'builtin':
        conf = frame['meta'].get('confidence') or {}
        report += [f'> ⚠ 可靠性声明: 塔型 {frame["meta"]["tower"]} 非内置型号, 几何来自通用解析'
                   f'(parse_mode={pm}, 方法={frame["meta"].get("parse_method", "")}, '
                   f'置信度 body={conf.get("body", "?")}/crossarms={conf.get("crossarms", "?")}'
                   f'/scale={conf.get("scale", "?")})。',
                   '> 模型仅作演示参考, 不可用于下料加工。', '']
        for w in frame['meta'].get('warnings', [])[:20]:
            report.append(f'> - {w}')
        report.append('')
    report += [f'- 杆件: {stats["members"]}, 连接净隙 gap={stats["gap_mm"]}mm',
              f'- 端头回退: {stats["trim_ends"]} 端, 平均 {stats["trim_avg_mm"]}mm, 最大 {stats["trim_max_mm"]}mm',
              f'- 件号覆盖: {stats["piece_matched"]}/{stats["members"]} ({stats["piece_coverage"]*100:.0f}%)',
              f'- 规格取图纸明细表: {stats.get("spec_drawing", 0)} 杆',
              f'- 碰撞: {stats["collisions"]} (X撑设计交叉 {stats["xcross"]})',
              f'- 杆身穿透(拆件后): {stats["penetrations"]}', '',
              '## 检查项', '']
    for f_ in findings:
        icon = {'ok': '✅', 'warn': '⚠️', 'error': '❌'}[f_['level']]
        report.append(f'- {icon} {f_["msg"]}')
    report += ['', '## 产物清单', '',
               '- frame.json / frame_fab.json — 轴线模型 / 拆件下料模型',
               '- cut_list.csv / bom.csv — 下料清单 / 材料表',
               '- tower_frame.scad / tower_frame_real.scad — 轴线 / 真实截面 OpenSCAD',
               '- tower_frame_real.stl — 真实截面实体 STL(任意三维软件可直接打开)',
               '- views_三视图.png — 正/侧/俯三视图', '']
    if llm:
        log('  [llm] 生成审查报告')
        txt = review_report(llm, {'stats': stats, 'findings': findings,
                                  'bom_top': [r[0][0] for r in bom_rows[:10]]})
        if txt:
            report += ['## LLM 审查意见', '', txt]
    with open(os.path.join(out_dir, 'report.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    log(f'完成 ({time.time()-t0:.0f}s) -> {out_dir}')
    return stats
