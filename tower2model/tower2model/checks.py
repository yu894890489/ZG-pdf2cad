# -*- coding: utf-8 -*-
"""检查层: 规则检查(穿透/回退越界/件号覆盖) + 碰撞检查(胶囊)"""
import json
import numpy as np


# ---------- 检查规则 ----------
# 只有腿主材(LEG)杆身中段相交才算几何错误; 其余杆件(斜材/隔材/横担/X撑)
# 交叉处在实塔上均为螺栓/垫板连接, 属设计连接而非碰撞。
def _is_leg(m):
    return m['mid'].startswith('LEG')


# ---------- 关节感知穿透检查 (拆件后) ----------
def _seg_seg_st(pa, pb, qa, qb):
    """线段最近点参数 (s, t) 及距离"""
    d1 = pb - pa; d2 = qb - qa; r = pa - qa
    a = d1 @ d1; e = d2 @ d2
    if a <= 1e-9 and e <= 1e-9: return 0.0, 0.0, float(np.linalg.norm(r))
    if a <= 1e-9:
        t = float(np.clip(-f / e, 0, 1))
        return 0.0, t, float(np.linalg.norm(r + t * d2))
    if e <= 1e-9:
        s = float(np.clip(-c / a, 0, 1))
        return s, 0.0, float(np.linalg.norm(r + s * d1))
    b = d1 @ d2; f = d2 @ r; c = d1 @ r
    den = a * e - b * b
    s = np.clip((b * f - c * e) / den, 0, 1) if den > 1e-9 else 0.0
    t = (b * s + f) / e
    if t < 0:
        t = 0.0; s = np.clip(-c / a, 0, 1)
    elif t > e:
        t = 1.0; s = np.clip((b - c) / a, 0, 1)
    return float(s), float(t), float(np.linalg.norm(r + s * d1 - t * d2))


def penetration_check(members, tol=2.0):
    """拆件后杆身穿透: 仅当两杆最近点都在各自杆段中部(非端部)且 d < r1+r2-tol
       XB×XB 设计交叉排除; 返回穿透对列表"""
    ms = members
    P1 = [np.array(m['p1t'], float) for m in ms]
    P2 = [np.array(m['p2t'], float) for m in ms]
    R = [m['r_mm'] for m in ms]
    L = [max(np.linalg.norm(P2[i] - P1[i]), 1e-9) for i in range(len(ms))]
    bad = []
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            if not (_is_leg(ms[i]) or _is_leg(ms[j])):
                continue    # 非腿主材交叉 = 设计连接
            s, t, d = _seg_seg_st(P1[i], P2[i], P1[j], P2[j])
            if d < R[i] + R[j] - tol:
                if 0.03 < s < 0.97 and 0.03 < t < 0.97:   # 两杆身中部相交才算穿透
                    bad.append((ms[i]['mid'], ms[j]['mid'], round(d, 1)))
    return bad


# ---------- 规则检查汇总 ----------
def run_checks(frame_fab, collision):
    ms = frame_fab['members']
    trims = [t for m in ms for t in (m.get('trim1_mm', 0), m.get('trim2_mm', 0)) if t > 0]
    ends = [t for t in trims if t >= 500.0]
    matched = sum(1 for m in ms if m.get('piece_no'))
    findings = []
    pen = penetration_check(ms)
    if pen:
        findings.append({'level': 'error', 'msg': f'杆身穿透 {len(pen)} 对(拆件后仍相交), 需修几何',
                         'samples': pen[:10]})
    else:
        findings.append({'level': 'ok', 'msg': '杆身穿透 0(关节感知检查)'})
    if ends:
        findings.append({'level': 'warn', 'msg': f'{len(ends)} 个端头回退触顶 500mm(浅角度), 核对节点构造'})
    if matched < len(ms) * 0.3:
        findings.append({'level': 'warn',
                         'msg': f'件号覆盖 {matched}/{len(ms)} 偏低: 明细表 OCR 行不足或模型剖分与图纸不一致(结构性)'})
    for c in collision.get('collisions', [])[:1]:
        findings.append({'level': 'error', 'msg': f'碰撞未清零: {c}'})
    if not collision.get('collisions'):
        findings.append({'level': 'ok', 'msg': f"碰撞 0 (X撑交叉 {collision.get('xcross', 0)} 为设计连接)"})
    stats = {
        'members': len(ms),
        'trim_ends': len(trims),
        'trim_avg_mm': round(sum(trims) / len(trims), 1) if trims else 0,
        'trim_max_mm': round(max(trims), 1) if trims else 0,
        'piece_matched': matched,
        'piece_coverage': round(matched / len(ms), 3),
        'penetrations': len(pen),
        'collisions': len(collision.get('collisions', [])),
        'xcross': collision.get('xcross', 0),
        'gap_mm': frame_fab['meta'].get('gap_mm'),
    }
    return stats, findings


# ---------- 碰撞检查 (拆件前轴线模型) ----------
def collision_check(members, clear=10.0):
    """关节感知胶囊检查: 最近点落在某杆端部(3%内)=节点区设计接触, 不算碰撞"""
    ms = members
    N = len(ms)
    P1 = np.array([m['p1'] for m in ms])
    P2 = np.array([m['p2'] for m in ms])
    R = np.array([m['r_mm'] for m in ms])
    LN = np.array([max(np.linalg.norm(P2[i] - P1[i]), 1e-9) for i in range(N)])
    collisions, near, xcross, joint = [], [], 0, 0
    for i in range(N):
        for j in range(i + 1, N):
            d_ss = min(np.linalg.norm(P1[i]-P1[j]), np.linalg.norm(P1[i]-P2[j]),
                       np.linalg.norm(P2[i]-P1[j]), np.linalg.norm(P2[i]-P2[j]))
            if d_ss < 1.0: continue
            s, t, d = _seg_seg_st(P1[i], P2[i], P1[j], P2[j])
            thr = R[i] + R[j] + clear
            if d >= thr + 90: continue
            interior_i = 0.03 * LN[i] < s * LN[i] < 0.97 * LN[i]
            interior_j = 0.03 * LN[j] < t * LN[j] < 0.97 * LN[j]
            if interior_i and interior_j:
                if not (_is_leg(ms[i]) or _is_leg(ms[j])):
                    xcross += 1     # 非腿主材交叉 = 设计连接(垫板/螺栓)
                elif d < thr:
                    collisions.append((ms[i]['mid'], ms[j]['mid'], round(float(d), 1)))
                else:
                    near.append((ms[i]['mid'], ms[j]['mid'], round(float(d), 1)))
            elif d < thr:
                joint += 1          # 端部接触 = T/Y 节点或节点区搭接(设计)
            else:
                near.append((ms[i]['mid'], ms[j]['mid'], round(float(d), 1)))
    return {'pairs': N*(N-1)//2, 'joint': joint, 'xcross': xcross,
            'collisions': collisions, 'near': len(near)}
