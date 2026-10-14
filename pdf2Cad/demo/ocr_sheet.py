# -*- coding: utf-8 -*-
"""OCR 指定图纸页 -> 文字块列表"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import fitz, numpy as np
from rapidocr_onnxruntime import RapidOCR

num = sys.argv[1] if len(sys.argv) > 1 else '002'
ocr = RapidOCR()
doc = fitz.open(f'图纸/pdf/37-SA36901S-T0121-{num}.pdf')
page = doc[0]
pix = page.get_pixmap(dpi=200)
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
if pix.n == 4:
    img = img[:, :, :3]
result, _ = ocr(img)
print(f'{num}: boxes={len(result)}')
rows = []
for box, text, conf in result:
    xs = [p[0] for p in box]; ys = [p[1] for p in box]
    rows.append((float(np.mean(ys)), float(np.mean(xs)), text, float(conf)))
rows.sort(key=lambda r: (-r[0], r[1]))
with open(f'demo/ocr{num}.txt', 'w', encoding='utf-8') as f:
    for y, x, c, t in [(y, x, c, t) for y, x, t, c in rows]:
        f.write(f'{y:8.1f} {x:8.1f} {c:.2f} {t}\n')
print(f'saved demo/ocr{num}.txt')
