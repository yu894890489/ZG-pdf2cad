# -*- coding: utf-8 -*-
"""OCR 001 图纸, 输出全部文字块及位置 (用于定位材料明细表)"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import fitz, numpy as np
from rapidocr_onnxruntime import RapidOCR

ocr = RapidOCR()
doc = fitz.open('图纸/pdf/37-SA36901S-T0121-001.pdf')
page = doc[0]
pix = page.get_pixmap(dpi=150)
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
if pix.n == 4:
    img = img[:, :, :3]
print(f'page: {pix.width}x{pix.height}')

result, _ = ocr(img)
print('boxes:', len(result))
rows = []
for box, text, conf in result:
    xs = [p[0] for p in box]; ys = [p[1] for p in box]
    rows.append((float(np.mean(ys)), float(np.mean(xs)), text, float(conf)))
rows.sort(key=lambda r: (-r[0], r[1]))
with open('demo/ocr001.txt', 'w', encoding='utf-8') as f:
    for y, x, t, c in rows:
        f.write(f'{y:8.1f} {x:8.1f} {c:.2f} {t}\n')
print('saved demo/ocr001.txt')
