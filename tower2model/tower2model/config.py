# -*- coding: utf-8 -*-
"""tower2model 配置: 文件 config.yaml > 环境变量 > 内置默认
config.yaml 示例见 config.example.yaml
"""
import os, sys
if sys.version_info >= (3, 9):
    import ast

DEFAULTS = {
    'gap_mm': 3.0,          # 连接净隙
    'ocr_dpi': 200,         # 明细表 OCR 分辨率(300 更准但慢3倍)
    'ocr_tile': 2400,       # 分块尺寸
    'max_trim': 500.0,      # 端头回退上限
    'openscad': '',         # 留空自动找 vendor/openscad/openscad.exe
    'llm_api_base': '',     # OpenAI 兼容, 如 http://127.0.0.1:8000/v1 (空=不启用LLM)
    'llm_api_key': '',
    'llm_model': '',
}

def load_config(cfg_path=None):
    cfg = dict(DEFAULTS)
    # 环境变量
    for k in list(DEFAULTS):
        v = os.environ.get('T2M_' + k.upper())
        if v is not None:
            cfg[k] = _cast(DEFAULTS[k], v)
    # yaml 文件 (仅解析平层 key: value, 不引依赖)
    p = cfg_path or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')
    if os.path.exists(p):
        for ln in open(p, encoding='utf-8'):
            ln = ln.split('#', 1)[0].strip()
            if ':' not in ln: continue
            k, v = (s.strip() for s in ln.split(':', 1))
            if k in DEFAULTS and v != '':
                cfg[k] = _cast(DEFAULTS[k], v)
    return cfg

def _cast(default, v):
    if isinstance(default, float):
        try: return float(v)
        except ValueError: return default
    if isinstance(default, int):
        try: return int(v)
        except ValueError: return default
    return v

def find_openscad(cfg):
    """vendor 打包版 > 指定路径 > 常见安装位置 > PATH; 返回 exe 路径或 None"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cand = [cfg.get('openscad'),
            os.path.join(root, 'vendor', 'openscad', 'openscad.exe'),
            r'C:\Program Files\OpenSCAD\openscad.exe',
            r'D:\Program Files\OpenSCAD\openscad.exe']
    for c in cand:
        if c and os.path.exists(c):
            return c
    return None
