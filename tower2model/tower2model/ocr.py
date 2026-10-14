# -*- coding: utf-8 -*-
"""分块 OCR 明细表 (rapidocr): 每张图纸 -> work/ocr/ocrNNN.txt (y x conf text)
GPU(DirectML) 推理 + 多图纸线程并发(每线程复用一个 OCR 会话)"""
import os, sys, threading
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np

_TLS = threading.local()
_TLS_INIT_LOCK = threading.Lock()

def _get_ocr():
    """线程本地 OCR 会话(GPU 探测一次, 失败回退 CPU)"""
    if getattr(_TLS, 'ocr', None) is not None:
        return _TLS.ocr
    from rapidocr_onnxruntime import RapidOCR
    try:
        kw = dict(det_use_dml=True, cls_use_dml=True, rec_use_dml=True)
        o = RapidOCR(**kw)
        if 'DmlExecutionProvider' not in o.text_det.infer.session.get_providers():
            raise RuntimeError('DML not active')
        print('  [ocr] GPU (DirectML)', flush=True)
    except Exception:
        o = RapidOCR()
        print('  [ocr] CPU', flush=True)
    _TLS.ocr = o
    return o

def ocr_sheet(pdf_path, out_path, dpi=200, tile=2400):
    """渲染整页 -> 切瓦片 -> OCR -> 合并全局坐标; 已有结果跳过"""
    if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
        return 'skip'
    import fitz
    ocr = _get_ocr()
    doc = fitz.open(pdf_path)
    pix = doc[0].get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4: img = img[:, :, :3]
    H, W = img.shape[:2]
    rows = []
    for y0 in range(0, H, tile):
        for x0 in range(0, W, tile):
            t = img[y0:y0+tile, x0:x0+tile]
            if t.shape[0] < 60 or t.shape[1] < 60: continue
            res, _ = ocr(t)
            if not res: continue
            for box, text, conf in res:
                xs = [p[0] for p in box]; ys = [p[1] for p in box]
                rows.append((y0+float(np.mean(ys)), x0+float(np.mean(xs)), text, float(conf)))
    seen = set(); uniq = []
    for r in sorted(rows, key=lambda r: (-r[0], r[1])):
        k = (round(r[0]/5), round(r[1]/5), r[2])
        if k in seen: continue
        seen.add(k); uniq.append(r)
    with open(out_path, 'w', encoding='utf-8') as f:
        for y, x, t, c in uniq:
            f.write(f'{y:8.1f} {x:8.1f} {c:.2f} {t}\n')
    return f'{len(uniq)} boxes'

def batch_ocr(pdf_dir, ocr_dir, sheets=None, dpi=200, tile=2400, workers=None):
    """扫描 *-NNN.pdf 图纸批量 OCR; 返回 {sheet: pdf_path}; sheets=None 全部
    workers: 并发进程数, 默认环境变量 T2M_OCR_WORKERS, 再默认 1。
    实测单 GPU 下 workers>1 无收益(DML 推理排队, 0.68x), 多卡场景才值得开"""
    import glob, re
    found = {}
    for p in glob.glob(os.path.join(pdf_dir, '*.pdf')):
        m = re.search(r'-(\d{3})\.pdf$', p)
        if m:
            found[m.group(1)] = p
            continue
        # 兼容客户整卷导出的 xxx_1.pdf 序号页, 零填充成 001/002...
        m = re.search(r'[_-](\d{1,3})\.pdf$', p)
        if m: found.setdefault(f'{int(m.group(1)):03d}', p)
    os.makedirs(ocr_dir, exist_ok=True)
    todo = sheets if sheets else sorted(found)
    workers = max(1, int(workers or os.environ.get('T2M_OCR_WORKERS') or 1))
    tasks = [(s, found[s], os.path.join(ocr_dir, f'ocr{s}.txt'))
             for s in todo if s in found]
    out = {}
    if workers == 1 or len(tasks) <= 1:
        for k, (s, p, op) in enumerate(tasks):
            out[s] = p
            print(f'  [{k+1}/{len(tasks)}] {s}: {ocr_sheet(p, op, dpi, tile)}', flush=True)
    else:
        # 注意: DML 多线程会死锁 -> 多进程, 每进程独立 GPU 上下文
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor
        ctx = multiprocessing.get_context('spawn')
        n_done = 0
        with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as ex:
            for s, p, r in ex.map(_ocr_one, [(s, p, op, dpi, tile) for s, p, op in tasks]):
                out[s] = p
                n_done += 1
                print(f'  [{n_done}/{len(tasks)}] {s}: {r}', flush=True)
    return out


def _ocr_one(args):
    """进程池 worker: 独立进程内初始化 OCR 会话并处理一张图"""
    s, p, op, dpi, tile = args
    return s, p, ocr_sheet(p, op, dpi, tile)
