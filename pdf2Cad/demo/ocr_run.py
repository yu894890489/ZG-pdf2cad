# -*- coding: utf-8 -*-
"""Step 3: OCR the whole sheet, cache results mapped to PDF coordinates."""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
import fitz
from rapidocr_onnxruntime import RapidOCR

PDF = '图纸/37-SA36901S-T0121-050.pdf'
DPI = 150
doc = fitz.open(PDF)
page = doc[0]
pix = page.get_pixmap(dpi=DPI)
img_path = 'demo/page_full.png'
pix.save(img_path)
pw, ph = pix.width, pix.height
doc.close()

ocr = RapidOCR()
res, _ = ocr(img_path)
items = []
for box, text, conf in res:
    xs = [p[0] for p in box]; ys = [p[1] for p in box]
    items.append({
        'text': text, 'conf': round(float(conf), 3),
        'px_bbox': [min(xs), min(ys), max(xs), max(ys)],
        'bbox': [round(v * 72.0 / DPI, 1) for v in (min(xs), min(ys), max(xs), max(ys))],
    })
json.dump({'dpi': DPI, 'page_px': [pw, ph], 'items': items},
          open('demo/ocr.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'OCR items: {len(items)}')
avg = sum(i['conf'] for i in items) / len(items)
print(f'avg conf: {avg:.3f}')
