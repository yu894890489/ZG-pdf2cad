# -*- coding: utf-8 -*-
"""分块 OCR 大幅面图纸: 渲染整页 -> 切成瓦片 -> OCR -> 合并全局坐标"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import fitz, numpy as np
from rapidocr_onnxruntime import RapidOCR

num = sys.argv[1]
DPI = int(sys.argv[2]) if len(sys.argv) > 2 else 200
TILE = int(sys.argv[3]) if len(sys.argv) > 3 else 2400
ocr = RapidOCR()
doc = fitz.open(f'图纸/pdf/37-SA36901S-T0121-{num}.pdf')
pix = doc[0].get_pixmap(dpi=DPI)
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
if pix.n == 4: img = img[:, :, :3]
H, W = img.shape[:2]
print(f'{num}: {W}x{H}')

rows = []
for y0 in range(0, H, TILE):
    for x0 in range(0, W, TILE):
        tile = img[y0:y0+TILE, x0:x0+TILE]
        if tile.shape[0] < 60 or tile.shape[1] < 60: continue
        res, _ = ocr(tile)
        if not res: continue
        for box, text, conf in res:
            xs = [p[0] for p in box]; ys = [p[1] for p in box]
            rows.append((y0+float(np.mean(ys)), x0+float(np.mean(xs)), text, float(conf)))
# 去重 (瓦片重叠区域无重叠, 但同位置跨瓦片可能有; 简单按 y,x,text 去重)
seen = set(); uniq = []
for r in sorted(rows, key=lambda r: (-r[0], r[1])):
    k = (round(r[0]/5), round(r[1]/5), r[2])
    if k in seen: continue
    seen.add(k); uniq.append(r)
with open(f"demo/ocr{num}{'_'+str(DPI) if DPI!=200 else ''}.txt", 'w', encoding='utf-8') as f:
    for y, x, t, c in uniq:
        f.write(f'{y:8.1f} {x:8.1f} {c:.2f} {t}\n')
print(f'boxes: {len(uniq)} -> demo/ocr{num}{"_"+str(DPI) if DPI!=200 else ""}.txt')
