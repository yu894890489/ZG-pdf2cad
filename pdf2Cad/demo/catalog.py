# -*- coding: utf-8 -*-
"""Catalog all 165 sheets: title block OCR + geometry stats. Output catalog JSON + HTML index."""
import fitz, os, sys, json, re, math
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

PDF_DIR = '图纸'
OUT = 'demo/catalog.json'
OUT_HTML = 'demo/catalog.html'
THUMB_DIR = 'demo/catalog_thumbs'
os.makedirs(THUMB_DIR, exist_ok=True)

ocr = RapidOCR()
files = sorted(f for f in os.listdir(PDF_DIR)
               if f.startswith('37-SA36901S-T0121-') and f.endswith('.pdf') and '-ML-' not in f)
print(f'sheets: {len(files)}')

catalog = []
for idx, f in enumerate(files):
    mnum = re.search(r'-(\d+)\.pdf$', f)
    num = int(mnum.group(1)) if mnum else 0
    doc = fitz.open(os.path.join(PDF_DIR, f))
    page = doc[0]
    paths = page.get_drawings()
    n_paths = len(paths)
    # thumbnail
    pix = page.get_pixmap(dpi=22)
    tf = os.path.join(THUMB_DIR, f'{num:03d}.png')
    pix.save(tf)
    # title block OCR (bottom-right region)
    tb = fitz.Rect(page.rect.width - 600, page.rect.height - 240,
                   page.rect.width, page.rect.height)
    pix2 = page.get_pixmap(dpi=180, clip=tb)
    tb_img = f'demo/titles/tb_{num:03d}.png'
    os.makedirs('demo/titles', exist_ok=True)
    pix2.save(tb_img)
    res, _ = ocr(tb_img)
    text = ' '.join(t for _, t, _ in (res or []))
    # guess sheet type from keywords
    title = ''
    m = re.search(r'(地线支架|上导线横担|中导线横担|下导线横担|身部结构图|总图|基础|施工|说明|目录)[^图]*图?', text)
    if m: title = m.group(0)
    else:
        # fallback: use the widest text fragment
        frags = [t for _, t, _ in (res or []) if len(t) > 4]
        title = frags[0] if frags else '(未识别)'
    catalog.append({
        'num': num, 'file': f, 'paths': n_paths, 'title': title,
        'w': round(page.rect.width), 'h': round(page.rect.height),
        'thumb': tf,
    })
    if idx % 20 == 0:
        print(f'  {idx}/{len(files)}: {num} {title} paths={n_paths}')
    doc.close()

json.dump(catalog, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'saved {OUT}')

# HTML index page
html = ['''<!DOCTYPE html><html><head><meta charset="utf-8"><title>图纸目录</title>
<style>
body{font-family:'Microsoft YaHei',sans-serif;background:#0f1420;color:#dde4f0;margin:0;padding:20px}
h1{font-size:20px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.card{background:#171e2e;border:1px solid #26304a;border-radius:8px;padding:8px;font-size:12px}
.card img{width:100%;border-radius:4px;background:#fff}
.t{ color:#9fc1ff;font-weight:700; margin-top:4px }
.p{color:#8a94a8;font-size:11px}
</style></head><body><h1>图纸目录（165 张）</h1><div class="grid">''']
for c in catalog:
    rel = os.path.relpath(c['thumb'], 'demo').replace('\\', '/')
    html.append(f'''<div class="card"><img src="{rel}"><div class="t">{c["num"]:03d} {c["title"]}</div><div class="p">{c["paths"]} paths</div></div>''')
html.append('</div></body></html>')
open(OUT_HTML, 'w', encoding='utf-8').write(''.join(html))
print(f'saved {OUT_HTML}')
