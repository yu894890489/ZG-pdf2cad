# -*- coding: utf-8 -*-
"""CLI: python -m tower2model run <input_dir> [-o out] [--gap 3] [--dpi 200] ..."""
import argparse, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    ap = argparse.ArgumentParser(prog='tower2model',
                                 description='输电铁塔图纸 -> 三维模型/下料清单/三视图')
    sub = ap.add_subparsers(dest='cmd', required=True)

    r = sub.add_parser('run', help='全流程: PDF 明细表 -> 模型+下料+三视图+报告')
    r.add_argument('input', help='图纸 PDF 目录 (*-NNN.pdf)')
    r.add_argument('-o', '--out', default='outputs')
    r.add_argument('--gap', type=float, help='连接净隙 mm (默认 config 3)')
    r.add_argument('--dpi', type=int, help='OCR 分辨率 (默认 200, 300 更准更慢)')
    r.add_argument('--sheets', help='仅 OCR 这些图号, 逗号分隔如 004,007,013')
    r.add_argument('--ocr-cache', help='已有 OCR 结果目录(work/ocr), 跳过重复 OCR')
    r.add_argument('--no-llm', action='store_true', help='禁用 LLM')
    r.add_argument('--config', help='config.yaml 路径')

    c = sub.add_parser('check', help='对已有 frame_fab.json 重跑检查')
    c.add_argument('fab', help='frame_fab.json 路径')

    args = ap.parse_args()
    if args.cmd == 'run':
        from .pipeline import run
        sheets = args.sheets.split(',') if args.sheets else None
        run(args.input, args.out, gap=args.gap, dpi=args.dpi, sheets=sheets,
            ocr_cache=args.ocr_cache, no_llm=args.no_llm, cfg_path=args.config)
    elif args.cmd == 'check':
        import json
        from . import checks
        fab = json.load(open(args.fab, encoding='utf-8'))
        col = checks.collision_check(fab['members'])
        stats, findings = checks.run_checks(fab, col)
        for f in findings:
            icon = {'ok': 'OK ', 'warn': 'WARN', 'error': 'ERR '}[f['level']]
            print(f'[{icon}] {f["msg"]}')
        print(stats)


if __name__ == '__main__':
    main()
