# -*- coding: utf-8 -*-
"""用 accoreconsole.exe 批量转换 DWG->DXF(2004)"""
import os, sys, subprocess, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ACC = r'D:\Program Files\Autocad2025\AutoCAD 2025\accoreconsole.exe'
DWG_DIR = r'F:\workspace\orca\brainStorm\pdf2Cad\图纸\dxf和dwg'
OUT_DIR = r'F:\workspace\orca\brainStorm\pdf2Cad\demo\dxf_converted'
os.makedirs(OUT_DIR, exist_ok=True)

targets = ['001', '008', '100']
for num in targets:
    dwg = os.path.join(DWG_DIR, f'37-SA36901S-T0121-{num}.dwg')
    dxf = os.path.join(OUT_DIR, f'{num}.dxf')
    if not os.path.isfile(dwg):
        print(f'  {num}: dwg not found'); continue
    scr = os.path.join(OUT_DIR, f'{num}.scr')
    with open(scr, 'w', encoding='gbk') as sf:
        sf.write('_.DXFOUT\n' + dxf + '\n16\n\n\n')
    cmd = [ACC, '/i', dwg, '/s', scr, '/l', 'en-US']
    print(f'converting {num}...', flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                       errors='replace', cwd=os.path.dirname(ACC))
    if os.path.isfile(dxf):
        print(f'  OK: {dxf} ({os.path.getsize(dxf)/1e6:.1f} MB)')
    else:
        print(f'  FAIL rc={r.returncode} out={r.stdout[:80]} err={r.stderr[:80]}')
