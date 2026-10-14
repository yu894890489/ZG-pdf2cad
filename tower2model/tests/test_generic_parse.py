# -*- coding: utf-8 -*-
"""通用解析路径单测: 标定/VLM(mock)/校验修正/兜底链/规格挂接/SZK 回归"""
import os, sys, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

from tower2model import rebuild, generic_parse, specs


class FakeLLM:
    def __init__(self, params=None, fail=False):
        self.params = params or json.loads(json.dumps(TRUTH_PARAMS))
        self.fail = fail
        self.calls = 0
    def chat(self, *a, **kw):
        raise RuntimeError('fake')
    def chat_json(self, prompt, **kw):
        self.calls += 1
        if self.fail:
            raise RuntimeError('fake fail')
        return self.params


from tests.make_fixture_tower import make_fixture, TRUTH, TRUTH_PARAMS


@pytest.fixture(scope='module')
def fixture(tmp_path_factory):
    d = str(tmp_path_factory.mktemp('fixture'))
    pdf, ocr = make_fixture(d)
    return pdf, ocr


def test_calibrate_accuracy(fixture):
    pdf, ocr = fixture
    segs, page = generic_parse.extract_segments(pdf)
    assert segs, '矢量提取应有线段'
    bb = generic_parse.view_bbox(segs)
    sc, h, conf, method, _cands = generic_parse.calibrate(
        ocr, bb, page[1], 200, generic_parse.raw_h_spans(pdf))
    assert abs(h - TRUTH['height']) / TRUTH['height'] < 0.05, f'标定高度 {h} 偏差>5% ({method})'
    # 竖排全高标注漏读时, 底部宽度数字 + 水平线匹配仍应给出合理高度
    import tempfile, os as _os
    d = tempfile.mkdtemp()
    ocr2 = _os.path.join(d, 'ocr.txt')
    open(ocr2, 'w', encoding='utf-8').write('  2179.7  1654.0 0.99 6000\n')
    _, h2, _, m2, _ = generic_parse.calibrate(ocr2, bb, page[1], 200, generic_parse.raw_h_spans(pdf))
    assert abs(h2 - TRUTH['height']) / TRUTH['height'] < 0.1, f'宽度标定 {h2} 偏差>10% ({m2})'


def test_vlm_end_to_end(fixture, tmp_path):
    pdf, ocr = fixture
    frame = generic_parse.build_frame(pdf, ocr, FakeLLM(), str(tmp_path), lambda s: None, dpi=200)
    assert len(frame['members']) > 0
    assert frame['meta']['parse_mode'] == 'llm'
    top = max(max(m['p1'][2], m['p2'][2]) for m in frame['members'])
    assert abs(top - TRUTH['height']) / TRUTH['height'] < 0.05, f'塔顶 {top}'
    mids = ''.join(m['mid'][:2] for m in frame['members'])
    assert 'L1' in mids and 'L2' in mids, '应有 L1/L2 两层横担'


def test_validate_bad_json(fixture, tmp_path):
    pdf, ocr = fixture
    bad = json.loads(json.dumps(TRUTH_PARAMS))
    bad['body_profile'] = [[0, 3000], [10000, 5000], [8000, 2000], [30000, 600]]  # z 非单调+负坡
    bad['crossarms'] = [{'name': 'L1', 'z_bottom': 10000, 'half_width_root': 500,
                         'half_width_tip': 300, 'top_pts': [[600, 11000], [900, 10900]],
                         'bot_pts': [[600, 10000], [900, 10000]]}]  # 未凸出塔身
    frame = generic_parse.build_frame(pdf, ocr, FakeLLM(bad), str(tmp_path), lambda s: None)
    assert frame['meta']['parse_mode'] == 'llm'
    assert frame['meta']['warnings'], '坏项应记录 repairs/warnings'
    prof = frame['meta'].get('body_profile') or generic_parse  # profile 在 params 里
    ms = frame['members']
    assert len(ms) > 0
    zs = [m['p1'][2] for m in ms]
    assert min(zs) >= -1.0, '塔底应归零'
    # 丢弃未凸出横担后应补默认横担
    assert any(m['mid'].startswith('L') for m in ms)


def test_fallback_chain(fixture, tmp_path):
    pdf, ocr = fixture
    # 级别 3: llm=None -> vector_only
    frame = generic_parse.build_frame(pdf, ocr, None, str(tmp_path), lambda s: None)
    assert frame['meta']['parse_mode'] == 'vector_only'
    assert len(frame['members']) > 0
    # 级别 4: 空白 PDF(无矢量) -> fallback_default
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    blank = os.path.join(str(tmp_path), 'blank.pdf')
    f = plt.figure(figsize=(8, 6))  # 无轴无内容 -> 零矢量线段
    f.savefig(blank); plt.close(f)
    frame = generic_parse.build_frame(blank, ocr, None, str(tmp_path), lambda s: None)
    assert frame['meta']['parse_mode'] == 'fallback_default'
    assert len(frame['members']) > 0
    # VLM 异常但矢量可用 -> vector_only
    frame = generic_parse.build_frame(pdf, ocr, FakeLLM(fail=True), str(tmp_path), lambda s: None)
    assert frame['meta']['parse_mode'] == 'vector_only'
    assert len(frame['members']) > 0


def test_attach_generic(tmp_path):
    frame = rebuild.build_frame_from_params(dict(generic_parse.DEFAULT_PARAMS))
    rows = {'004': [{'spec': 'L63x5', 'len': 5000}, {'spec': 'L63x5', 'len': 5010},
                    {'spec': 'L140x10', 'len': 12000}]}
    rp = os.path.join(str(tmp_path), 'rows.json')
    json.dump(rows, open(rp, 'w', encoding='utf-8'))
    n = specs.attach_generic(frame, rp)
    assert n > 0
    assert frame['meta']['spec_level'].startswith('不可靠')
    specs.write_bom(frame, os.path.join(str(tmp_path), 'bom.csv'))
    # 空行池 -> 全部角色默认
    frame2 = rebuild.build_frame_from_params(dict(generic_parse.DEFAULT_PARAMS))
    n2 = specs.attach_generic(frame2, os.path.join(str(tmp_path), 'nofile.json'))
    assert n2 > 0


def test_szk_regression():
    old = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                      'tmp', '_baseline_frame.json'), encoding='utf-8'))
    assert rebuild.build_frame() == old
    assert rebuild.build_frame() == rebuild.build_frame_from_params(rebuild._SZK31102A_PARAMS)
