# -*- coding: utf-8 -*-
"""三层横担 3D 装配：008(中) + 011(下) 下平面提取 → 节点图 → 3D"""
import sys, os, json, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ezdxf
from collections import Counter

DXF_DIR = os.path.join('图纸', 'dxf和dwg')
OUT = 'demo/leaf_results'
os.makedirs(OUT, exist_ok=True)

def extract_clean(msp, min_line=5.0, min_vtx=5):
    lines, circles = [], []
    for e in msp:
        t = e.dxftype()
        if t == 'LINE':
            L = e.dxf.start.distance(e.dxf.end)
            if L > min_line:
                lines.append({'a': [e.dxf.start.x, e.dxf.start.y],
                              'b': [e.dxf.end.x, e.dxf.end.y], 'len': L})
        elif t == 'LWPOLYLINE':
            pts = e.get_points('xy')
            if len(pts) > min_vtx:
                for i in range(len(pts)-1):
                    d = math.dist(pts[i][:2], pts[i+1][:2])
                    if d > min_line:
                        lines.append({'a': list(pts[i][:2]),
                                      'b': list(pts[i+1][:2]), 'len': d})
        elif t == 'CIRCLE':
            circles.append({'c': [e.dxf.center.x, e.dxf.center.y], 'r': e.dxf.radius})
    return lines, circles

def cluster_axes(lines, min_ext=15):
    n = len(lines)
    if n == 0: return []
    parent = list(range(n))
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    P = []
    for c in lines:
        dx, dy = c['b'][0]-c['a'][0], c['b'][1]-c['a'][1]
        L = math.hypot(dx, dy) or 1
        P.append((dx/L, dy/L, c['a'][0], c['a'][1], L))
    def colinear(i, j):
        uxi,uyi,axi,ayi,Li = P[i]
        uxj,uyj,axj,ayj,Lj = P[j]
        dot = uxi*uxj + uyi*uyj
        if abs(dot) < 0.9985: return False
        if dot < 0: uxj,uyj = -uxj,-uyj
        perp = abs(uxj*(ayi-ayj) - uyj*(axi-axj))
        if perp > 2.5: return False
        t1 = (axj-axi)*uxi + (ayj-ayi)*uyi
        return (t1+Lj) > -4 and t1 < Li+4
    buckets = {}
    for i,c in enumerate(lines):
        ang = round(math.degrees(math.atan2(P[i][1],P[i][0]))%180/3)
        buckets.setdefault(ang,[]).append(i)
    for key,idxs in buckets.items():
        for bi in range(len(idxs)):
            for bj in range(bi+1,len(idxs)):
                i,j = idxs[bi],idxs[bj]
                ri,rj = find(i),find(j)
                if ri!=rj and colinear(i,j): parent[rj]=ri
    groups = {}
    for i in range(n): groups.setdefault(find(i),[]).append(i)
    axes = []
    for idxs in groups.values():
        uxi,uyi,ox,oy,_ = P[idxs[0]]
        if uxi<0: uxi,uyi = -uxi,-uyi
        ts = []
        for i in idxs:
            for p in (lines[i]['a'], lines[i]['b']):
                ts.append((p[0]-ox)*uxi + (p[1]-oy)*uyi)
        t0,t1 = min(ts),max(ts)
        if t1-t0 < min_ext: continue
        axes.append({'a':[ox+uxi*t0,oy+uyi*t0], 'b':[ox+uxi*t1,oy+uyi*t1],
                     'ext':t1-t0, 'nseg':len(idxs)})
    return axes

def assemble_3d(axes, SC, D_ROOT=4600.0, D_TIP=800.0):
    by_ext = sorted(axes, key=lambda a: -a['ext'])
    maxext = by_ext[0]['ext'] if by_ext else 0
    def perp_off(c1, c2):
        dx, dy = c1['b'][0]-c1['a'][0], c1['b'][1]-c1['a'][1]
        L = math.hypot(dx,dy) or 1
        ux,uy = dx/L, dy/L
        return abs(-(c2['a'][0]-c1['a'][0])*uy + (c2['a'][1]-c1['a'][1])*ux)
    chord1 = by_ext[0]
    chord2 = next((c for c in by_ext[1:] if c['ext'] > maxext*0.7 and perp_off(chord1,c) > 50), None)
    if not chord2:
        chord2 = by_ext[1] if len(by_ext) > 1 else None
    if not chord2: return [], {}

    def orient(c):
        a,b = c['a'],c['b']
        return (a,b) if a[0]<=b[0] else (b,a)
    c1a,c1b = orient(chord1)
    c2a,c2b = orient(chord2)
    dA = math.dist(c1a,c2a); dB = math.dist(c1b,c2b)
    if dA > dB:
        c1a,c1b = c1b,c1a; c2a,c2b = c2b,c2a

    axA = [(c1a[0]+c2a[0])/2, (c1a[1]+c2a[1])/2]
    axB = [(c1b[0]+c2b[0])/2, (c1b[1]+c2b[1])/2]
    dd = math.dist(axA,axB) or 1
    aux,auy = (axB[0]-axA[0])/dd, (axB[1]-axA[1])/dd
    AXL = dd
    SEP_ROOT = min(dA,dB)*SC
    SEP_TIP = max(dA,dB)*SC
    AXL_MM = AXL*SC

    brac = [a for a in axes if a is not chord1 and a is not chord2 and a['ext'] > 20]

    nodes = []
    def snap(p, tol=4.0):
        for i,q in enumerate(nodes):
            if math.dist(p,q) < tol: return i
        nodes.append(list(p)); return len(nodes)-1
    members = []
    def add_mem(p1,p2,role,r):
        i1,i2 = snap(p1),snap(p2)
        if i1==i2: return
        members.append({'n1':i1,'n2':i2,'role':role,'r_mm':r})
    def proj(c,p):
        dx,dy = c['b'][0]-c['a'][0], c['b'][1]-c['a'][1]
        L = math.hypot(dx,dy) or 1
        return (p[0]-c['a'][0])*dx/L + (p[1]-c['a'][1])*dy/L
    def point_on(c,t):
        dx,dy = c['b'][0]-c['a'][0], c['b'][1]-c['a'][1]
        L = math.hypot(dx,dy) or 1
        return [c['a'][0]+dx/L*t, c['a'][1]+dy/L*t]

    stations = set()
    for b in brac:
        for p in (b['a'],b['b']):
            for cc in (chord1,chord2):
                t = proj(cc,p)
                if -5 <= t <= cc['ext']+5: stations.add(round(t/3)*3)
    stations = sorted(stations)
    merged = []
    for s in stations:
        if merged and s-merged[-1]<8: continue
        merged.append(s)

    for ci,c in enumerate([dict(a=c1a,b=c1b,ext=chord1['ext']),dict(a=c2a,b=c2b,ext=chord2['ext'])]):
        prev=None
        for s in merged:
            if s>c['ext']: break
            if prev is not None:
                add_mem(point_on(c,prev),point_on(c,s),f'下弦{ci+1}',110.0)
            prev=s
    for b in brac:
        add_mem(b['a'],b['b'],'平面斜材' if b['ext']>50 else '连接件',55.0)

    def n3d(p):
        t = (p[0]-axA[0])*aux + (p[1]-axA[1])*auy
        xn = max(0.0,min(1.0,t/AXL))
        oy = -(p[0]-axA[0])*auy + (p[1]-axA[1])*aux
        half = (SEP_ROOT/2)+(SEP_TIP/2-SEP_ROOT/2)*xn
        sign = 1 if oy>=0 else -1
        frac = min(1.0, abs(oy)/(max(dA,dB)/2+1e-9))
        return [round(t*SC,1), round(sign*half*frac,1), 0.0]

    m3d = []
    for m in members:
        w1,w2 = n3d(nodes[m['n1']]), n3d(nodes[m['n2']])
        if math.dist(w1,w2)<150: continue
        m3d.append({'role':m['role'],'r_mm':m['r_mm'],'p1':w1,'p2':w2})

    tip_x = AXL_MM
    for sgn in (1,-1):
        yr = sgn*SEP_ROOT/2; yt = sgn*SEP_TIP/2
        m3d.append({'role':'上弦(参数化)','r_mm':90.0,
            'p1':[0.0,round(yr,1),round(D_ROOT,1)],'p2':[round(tip_x,1),round(yt,1),round(D_TIP,1)]})
        m3d.append({'role':'根部竖杆(参数化)','r_mm':70.0,
            'p1':[0.0,round(yr,1),0.0],'p2':[0.0,round(yr,1),round(D_ROOT,1)]})
        m3d.append({'role':'侧面斜杆(参数化)','r_mm':55.0,
            'p1':[0.0,round(yr,1),round(D_ROOT,1)],
            'p2':[round(tip_x*0.4,1),round((yr+yt)/2,1),round((D_ROOT+D_TIP)/2,1)]})
        m3d.append({'role':'侧面斜杆(参数化)','r_mm':55.0,
            'p1':[round(tip_x*0.4,1),round((yr+yt)/2,1),round((D_ROOT+D_TIP)/2,1)],
            'p2':[round(tip_x,1),round(yt,1),round(D_TIP,1)]})

    prev=None
    for s in merged:
        if prev is not None and s-prev>8:
            p = point_on(dict(a=c1a,b=c1b),s)
            w = n3d(p)
            xn = min(1.0,s/AXL)
            zt = D_ROOT+(D_TIP-D_ROOT)*xn
            m3d.append({'role':'横隔竖杆','r_mm':45.0,
                'p1':[w[0],-w[1],0.0],'p2':[w[0],-w[1],round(zt,1)]})
            m3d.append({'role':'横隔横杆','r_mm':45.0,
                'p1':[w[0],-w[1],round(zt,1)],'p2':[w[0],w[1],round(zt,1)]})
        prev=s

    info = {'axis_mm':round(AXL_MM),'sep_root':round(SEP_ROOT),'sep_tip':round(SEP_TIP),
            'D_root':round(D_ROOT),'D_tip':round(D_TIP),'n_members':len(m3d)}
    return m3d, info

# ---- 三层横担装配 ----
LEVELS = [
    ('L2_mid', 114297.0, '008', 30.0, 4600.0, 800.0),
    ('L3_low',  99152.0, '011', 30.0, 4200.0, 700.0),
]

all_cross = {}
for label, ca_z, sheet, sc, dr, dt in LEVELS:
    f = os.path.join(DXF_DIR, f'37-SA36901S-T0121-{sheet}.dxf')
    if not os.path.isfile(f):
        print(f'{label}: {sheet}.dxf not found'); continue
    doc = ezdxf.readfile(f)
    msp = doc.modelspace()
    lines, circles = extract_clean(msp)
    axes = cluster_axes(lines)
    m3d, info = assemble_3d(axes, sc, dr, dt)
    X_OFF = 2238.0
    for m in m3d:
        m['p1'] = [round(m['p1'][0]+X_OFF,1), m['p1'][1], round(m['p1'][2]+ca_z,1)]
        m['p2'] = [round(m['p2'][0]+X_OFF,1), m['p2'][1], round(m['p2'][2]+ca_z,1)]
    mirrored = []
    for m in m3d:
        m2 = dict(m)
        m2['p1'] = [-m['p1'][0], m['p1'][1], m['p1'][2]]
        m2['p2'] = [-m['p2'][0], m['p2'][1], m['p2'][2]]
        m2['role'] = m['role']+'(镜像)'
        mirrored.append(m2)
    all_cross[label] = m3d + mirrored
    print(f'{label} ({sheet}): axis={info["axis_mm"]}mm spread={info["sep_root"]}->{info["sep_tip"]} '
          f'depth={info["D_root"]}->{info["D_tip"]} members={info["n_members"]}+{len(mirrored)}')

print(f'\ntotal crossarm members: {sum(len(v) for v in all_cross.values())}')
json.dump(all_cross, open('demo/all_crossarms_3d.json','w',encoding='utf-8'),
          ensure_ascii=False)
print('saved demo/all_crossarms_3d.json')
