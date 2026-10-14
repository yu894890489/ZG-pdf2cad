# -*- coding: utf-8 -*-
"""批量 OCR 分段图明细表 (后台跑, 每张约1-3分钟)
已有 200dpi OCR 的跳过; 完成后用 parse_schedule.py 批量解析再 fabricate.py 重新匹配件号
"""
import os, sys, time, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DPI = sys.argv[1] if len(sys.argv) > 1 else '200'
TILE = sys.argv[2] if len(sys.argv) > 2 else '2400'
SUFFIX = f'_{DPI}' if DPI != '200' else ''
HAVE = {'001', '004', '005', '007', '008', '010', '013', '060', '102', '110'}  # 已有 200dpi
sheets = [f'{i:03d}' for i in range(13, 127) if f'{i:03d}' not in HAVE or DPI != '200']
print(f'to OCR: {len(sheets)} sheets @ {DPI}dpi', flush=True)
t0 = time.time()
for k, s in enumerate(sheets):
    out = f'demo/ocr{s}{SUFFIX}.txt'
    if os.path.exists(out) and os.path.getsize(out) > 500:
        print(f'[{k+1}/{len(sheets)}] {s} exists, skip', flush=True)
        continue
    try:
        r = subprocess.run([sys.executable, 'demo/ocr_sheet_tiled.py', s, DPI, TILE],
                           capture_output=True, text=True, timeout=1200)
        tail = (r.stdout or '').strip().splitlines()[-1:] or ['(no output)']
        print(f'[{k+1}/{len(sheets)}] {s} ok {time.time()-t0:.0f}s | {tail[0]}', flush=True)
    except Exception as e:
        print(f'[{k+1}/{len(sheets)}] {s} FAIL: {e}', flush=True)
print(f'done in {(time.time()-t0)/60:.1f} min', flush=True)
