# -*- coding: utf-8 -*-
"""LLM 辅助层 (可选): OpenAI 兼容 /chat/completions, 纯 stdlib
未配置 api_base 时所有函数返回 None, 流水线自动走规则兜底
"""
import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import urllib.request

class LLM:
    def __init__(self, api_base, api_key, model, timeout=120, vision_model=None):
        self.base = api_base.rstrip('/')
        self.key = api_key
        self.model = model
        self.vision_model = vision_model or None
        self.timeout = timeout
        self.calls = 0

    @classmethod
    def from_config(cls, cfg):
        if not cfg.get('llm_api_base'):
            return None
        return cls(cfg['llm_api_base'], cfg.get('llm_api_key', ''),
                   cfg.get('llm_model') or 'default',
                   vision_model=cfg.get('llm_vision_model'))

    def chat(self, prompt, system='你是输电铁塔图纸数字化专家。只输出 JSON。', temperature=0.0,
             image_b64=None, model=None, timeout=None):
        """image_b64 非空时走 vision 消息(content 数组); model/timeout 可临时覆盖"""
        url = self.base + ('' if self.base.endswith('/chat/completions') else '/chat/completions')
        if image_b64:
            content = [{'type': 'text', 'text': prompt},
                       {'type': 'image_url',
                        'image_url': {'url': f'data:image/png;base64,{image_b64}'}}]
            # 读图优先用专门的视觉模型(配置 llm_vision_model)
            model = model or self.vision_model or self.model
        else:
            content = prompt
            model = model or self.model
        body = json.dumps({'model': model, 'temperature': temperature,
                           'messages': [{'role': 'system', 'content': system},
                                        {'role': 'user', 'content': content}]}).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.key}'})
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
            data = json.loads(r.read().decode('utf-8'))
        self.calls += 1
        return data['choices'][0]['message']['content']

    def chat_vision(self, prompt, image_b64, **kw):
        """读图: prompt + PNG base64 -> 文本"""
        return self.chat(prompt, image_b64=image_b64, **kw)

    def chat_json(self, prompt, **kw):
        """返回解析后的 JSON; 失败打印并返回 None (调用方可据此重试)"""
        try:
            txt = self.chat(prompt, **kw).strip()
            if txt.startswith('```'):
                txt = txt.strip('`').lstrip('json\n').rstrip('\n`')
            try:
                return json.loads(txt)
            except json.JSONDecodeError:
                # 思考模型常在 JSON 后附解释文字, 取首个 JSON 对象
                obj, _ = json.JSONDecoder().raw_decode(txt)
                return obj
        except Exception as e:
            print(f'  [llm] json 解析失败: {e}', flush=True)
            return None


# ---------- 具体任务 ----------
def clean_schedule_rows(llm, sheet, rows):
    """OCR 明细表行清洗: 传入 raw 行文本, 让 LLM 修正 编号/规格/长度/数量
    rows: [{'no','spec','len','qty','raw'}] -> 返回修正后的同结构列表 (失败返回 None)
    """
    if not llm or not rows: return None
    items = [{'i': i, 'raw': r['raw']} for i, r in enumerate(rows)]
    prompt = (
        f'下面是从输电铁塔图纸第 {sheet} 张明细表 OCR 出来的行, raw 为 OCR 原始拼接文本。\n'
        '角钢规格形如 L125x8, 钢管 φ660x14, 钢板 -8x60。\n'
        '请逐行修正出: no(件号数字), spec(规格), len(长度mm整数或null), qty(数量整数或null)。\n'
        '注意 OCR 常把 L 丢失、φ 丢失、数字粘连。无法判断的字段用 null。只输出 JSON 数组:\n'
        f'{json.dumps(items, ensure_ascii=False)}')
    out = llm.chat_json(prompt)
    if not isinstance(out, list) or len(out) != len(rows): return None
    fixed = []
    for r, o in zip(rows, out):
        m = dict(r)
        for k in ('no', 'spec', 'len', 'qty'):
            if isinstance(o.get(k), (int, str)) and o[k] not in ('', 'null', None):
                m[k] = o[k] if k in ('no', 'spec') else (int(o[k]) if str(o[k]).isdigit() else m[k])
        fixed.append(m)
    return fixed


def review_report(llm, ctx):
    """审查汇总: ctx = checks/collision/bom 统计 dict -> 中文报告文本 (失败 None)"""
    if not llm: return None
    prompt = (
        '以下是输电铁塔三维建模流水线的自动检查结果(JSON)。请写一份简明的中文审查报告(Markdown), '
        '包含: 1)结果解读 2)异常/风险点排序 3)下一步人工复核建议。直接输出 Markdown 正文。\n'
        + json.dumps(ctx, ensure_ascii=False, default=str)[:8000])
    try:
        return llm.chat(prompt, system='你是钢结构数字化评审专家, 输出简体中文 Markdown 报告。', temperature=0.2)
    except Exception as e:
        print(f'  [llm] 报告生成失败: {e}', flush=True)
        return None
