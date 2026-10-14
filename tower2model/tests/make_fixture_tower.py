# -*- coding: utf-8 -*-
"""合成夹具: 双横担层塔正视图 PDF (替代真实异型图纸做端到端验证)
塔型 SZT45000X, 高 30000mm, 半根开 3000mm, 两层横担(z=24000/28000)
用法: python tests/make_fixture_tower.py [输出目录]
"""
import os, sys

TRUTH = {
    'tower': 'SZT45000X', 'height': 30000.0, 'root_half': 3000.0,
    'profile': [(0.0, 3000.0), (18000.0, 1200.0), (20000.0, 1100.0), (30000.0, 600.0)],
    'diaphragm_z': [4500.0, 9000.0, 13500.0, 18000.0, 20000.0, 24000.0, 26000.0, 28000.0, 30000.0],
    'crossarm_bottoms': [24000.0, 28000.0],
}

# VLM 应输出的参数 JSON(供 FakeLLM 用, 数值即真值)
TRUTH_PARAMS = {
    'tower_type': TRUTH['tower'], 'total_height_mm': 30000, 'root_half_width_mm': 3000,
    'body_profile': [[z, w] for z, w in TRUTH['profile']],
    'diaphragm_z': TRUTH['diaphragm_z'],
    'panels': ([{'z0': 4500*i, 'z1': 4500*(i+1), 'type': 'diamond'} for i in range(4)] +
               [{'z0': 18000+4000*i, 'z1': 18000+4000*(i+1), 'type': 'X'} for i in range(3)]),
    'crossarms': [
        {'name': 'L1', 'z_bottom': 24000, 'half_width_root': 600, 'half_width_tip': 300,
         'top_pts': [[900, 25500], [4200, 25100]], 'bot_pts': [[900, 24000], [4200, 24000]]},
        {'name': 'L2', 'z_bottom': 28000, 'half_width_root': 500, 'half_width_tip': 250,
         'top_pts': [[750, 29300], [3500, 29000]], 'bot_pts': [[750, 28000], [3500, 28000]]},
    ],
    'confidence': {'body': 'high', 'crossarms': 'high', 'scale': 'high'},
    'notes': '合成夹具塔',
}


def _w(z):
    pts = TRUTH['profile']
    for (z0, w0), (z1, w1) in zip(pts, pts[1:]):
        if z0 <= z <= z1:
            return w0 + (w1-w0)*(z-z0)/(z1-z0)
    return pts[-1][1]


def make_fixture(out_dir):
    """生成 fixture PDF + 模拟 OCR txt(尺寸数字按真实 pt 位置), 返回 (pdf, ocr) 路径"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    os.makedirs(out_dir, exist_ok=True)
    fig = plt.figure(figsize=(16.54, 11.69))  # A3 横版
    ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
    ax.set_xlim(-7000, 7000); ax.set_ylim(-2600, 33000)
    ax.set_aspect('equal'); ax.axis('off')

    segs = []  # (x0,z0,x1,z1) 数据坐标, 同时用于画图
    P = TRUTH['profile']
    for sx in (1, -1):  # 腿
        segs += [(sx*p[1], p[0], sx*q[1], q[0]) for p, q in zip(P, P[1:])]
    for z in TRUTH['diaphragm_z']:  # 横隔水平线
        segs.append((-_w(z), z, _w(z), z))
    for i in range(4):  # 菱形腹杆 0-18000(正视图投影)
        z0, z1 = 4500*i, 4500*(i+1); zm = (z0+z1)/2
        segs += [(-_w(z0), z0, 0, zm), (0, zm, _w(z1), z1),
                 (_w(z0), z0, 0, zm), (0, zm, -_w(z1), z1)]
    for i in range(3):  # X 腹杆 18000-30000
        z0, z1 = 18000+4000*i, 18000+4000*(i+1)
        segs += [(-_w(z0), z0, _w(z1), z1), (_w(z0), z0, -_w(z1), z1)]
    # 两层横担(上下弦 + 端竖杆 + 斜腹杆)
    arms = [dict(zb=24000., xr=900., xt=4200., zt=25500., tip_zt=25100.),
            dict(zb=28000., xr=750., xt=3500., zt=29300., tip_zt=29000.)]
    for a in arms:
        for sx in (1, -1):
            segs += [(sx*a['xr'], a['zb'], sx*a['xt'], a['zb']),
                     (sx*a['xr'], a['zt'], sx*a['xt'], a['tip_zt']),
                     (sx*a['xt'], a['zb'], sx*a['xt'], a['tip_zt']),
                     (sx*a['xr'], a['zb'], sx*a['xt'], a['tip_zt'])]
    for x0, z0, x1, z1 in segs:
        ax.plot([x0, x1], [z0, z1], 'k-', lw=0.7)
    # 尺寸标注(竖直全高在左侧视区外, 根开在底部)
    ax.plot([-5200, -5200], [0, 30000], 'k-', lw=0.5)
    ax.text(-5600, 15000, '30000', rotation=90, fontsize=11, ha='center', va='center')
    ax.plot([-3000, 3000], [-1200, -1200], 'k-', lw=0.5)
    ax.text(0, -1900, '6000', fontsize=11, ha='center')
    ax.text(0, -2400, 'TOWER TYPE SZT45000X  FRONT VIEW', fontsize=10, ha='center')

    pdf = os.path.join(out_dir, '01-FIXTURE-T0121-001.pdf')
    fig.savefig(pdf, format='pdf')
    plt.close(fig)

    # 模拟 OCR txt(y x conf text, px@200dpi): 用与保存一致的数据->pt 变换
    ocr = os.path.join(out_dir, 'ocr001.txt')
    fig = plt.figure(figsize=(16.54, 11.69))
    ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
    ax.set_xlim(-7000, 7000); ax.set_ylim(-2600, 33000)
    ax.set_aspect('equal'); ax.axis('off')
    fig.canvas.draw()  # 先触发 apply_aspect, 使 transData 与 PDF 实际渲染一致
    tr = ax.transData.transform
    page_h_px = fig.get_figheight() * fig.dpi * 2  # 200dpi 页高, 用于翻成自顶向下 y
    def to_px(x, z):
        dx, dy = tr((x, z))  # dpi=100 默认 -> px, dy 自底向上
        return dx*2, page_h_px - dy*2  # 换算到 200dpi 且 y 自顶向下(与 RapidOCR 一致)
    lines = []
    for x, z, txt in [(-5600, 15000, '30000'), (0, -1900, '6000'),
                      (0, -2400, 'TOWER TYPE SZT45000X FRONT VIEW')]:
        px, py = to_px(x, z)
        lines.append(f'{py:8.1f} {px:8.1f} 0.99 {txt}')
    open(ocr, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    plt.close(fig)
    return pdf, ocr


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'fixture')
    pdf, ocr = make_fixture(out)
    print(pdf)
    print(ocr)
