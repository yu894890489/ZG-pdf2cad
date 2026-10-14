# -*- coding: utf-8 -*-
"""008 下平面 -> 3D node-graph assembly -> inject as level-2 crossarm."""
import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')

d2 = json.load(open('demo/stageb2_008.json', encoding='utf-8'))
clusters, circles = d2['clusters'], d2['plan_circles']

# ---------- 1. chords: two double-line pairs -> midlines ----------
cand = [c for c in clusters if c['ext'] > 1500 and (abs(c['ang']-9.3) < 3 or abs(c['ang']-170.6) < 3)]
def midline(pa, pb):
    return {'a': [(pa['a'][0]+pb['a'][0])/2, (pa['a'][1]+pb['a'][1])/2],
            'b': [(pa['b'][0]+pb['b'][0])/2, (pa['b'][1]+pb['b'][1])/2],
            'ext': pa['ext'], 'ang': pa['ang']}
upper = [c for c in cand if c['a'][1] < 1000]
lower = [c for c in cand if c['a'][1] >= 1000]
chords = [midline(upper[0], upper[1]), midline(lower[0], lower[1])]
print('chords:')
for c in chords:
    print(f"  ({c['a'][0]:.0f},{c['a'][1]:.0f})-({c['b'][0]:.0f},{c['b'][1]:.0f}) ext={c['ext']:.0f} ang={c['ang']}")

# chord direction unit vectors
def unit(c):
    dx, dy = c['b'][0]-c['a'][0], c['b'][1]-c['a'][1]
    L = math.hypot(dx, dy)
    return dx/L, dy/L, L
u1, L1 = unit(chords[0])[0:2], unit(chords[0])[2]
u2, L2 = unit(chords[1])[0:2], unit(chords[1])[2]
# orient both chords tip->root: tip = the end closer to the other chord's tip
# tips are the LEFT ends (small x) per the view
def orient(c):
    a, b = c['a'], c['b']
    if a[0] > b[0]: a, b = b, a
    return a, b
c1a, c1b = orient(chords[0])
c2a, c2b = orient(chords[1])
u1 = ((c1b[0]-c1a[0])/L1, (c1b[1]-c1a[1])/L1)
u2 = ((c2b[0]-c2a[0])/L2, (c2b[1]-c2a[1])/L2)

# ---------- 2. node snap ----------
nodes = []
def snap(p, tol=25.0):
    for i, q in enumerate(nodes):
        if math.dist(p, q) < tol:
            return i
    nodes.append(list(p))
    return len(nodes) - 1

member_list = []
def add_member(p1, p2, role, r, rec=None):
    i1, i2 = snap(p1), snap(p2)
    if i1 == i2: return None
    member_list.append({'n1': i1, 'n2': i2, 'role': role, 'r_mm': r, 'rec': rec or {}})
    return member_list[-1]

# chords as node chains: place nodes along each chord at the bracing attachment x-positions
# collect bracing endpoints, project onto each chord -> node stations
brac = [c for c in clusters if c not in chords and c['ext'] > 80
        and 60 <= c['a'][0] <= 2240 and 540 <= c['a'][1] <= 1460
        and 60 <= c['b'][0] <= 2240 and 540 <= c['b'][1] <= 1460]
print(f'bracing axes: {len(brac)}')

def proj_on(c, p):
    ux, uy, L = unit(c)
    return (p[0]-c['a'][0])*ux + (p[1]-c['a'][1])*uy

def point_on(c, t):
    ux, uy, L = unit(c)
    return [c['a'][0]+ux*t, c['a'][1]+uy*t]

stations = set()
for c in brac:
    for p in (c['a'], c['b']):
        t1 = proj_on(chords[0], p)
        t2 = proj_on(chords[1], p)
        if -30 <= t1 <= L1 + 30: stations.add(round(t1 / 20) * 20)
        if -30 <= t2 <= L2 + 30: stations.add(round(t2 / 20) * 20)
stations = sorted(s for s in stations if 0 <= s <= max(L1, L2))
print(f'node stations on chords: {len(stations)}')

# merge near stations (<60pt)
merged = []
for s in stations:
    if merged and s - merged[-1] < 60: continue
    merged.append(s)
stations = merged
print(f'merged stations: {len(stations)}')

# build chord members between consecutive stations
chord_nodes = {}
for ci, (c, uu, LL) in enumerate([(chords[0], u1, L1), (chords[1], u2, L2)]):
    prev = None
    for s in stations:
        if s > LL: break
        p = point_on(c, s)
        ni = snap(p, tol=30)
        if prev is not None:
            add_member(point_on(c, merged_prev), point_on(c, s),
                       f'下弦{ci+1}(320{ci+1}类)', 110.0)
        prev, merged_prev = ni, s

# bracing members between chord nodes
for c in brac:
    i1 = snap(c['a'], tol=35)
    i2 = snap(c['b'], tol=35)
    if i1 == i2: continue
    role = 'X平面斜材' if c['ext'] > 300 else '横隔/连接件'
    add_member(c['a'], c['b'], role, 55.0)

print(f'nodes: {len(nodes)}, members: {len(member_list)}')

# ---------- 3. 3D placement (view = main truss elevation, rotated 9.3deg) ----------
SC = 10.6   # mm/pt (1:30)
# bottom chord line = chords[1] (lower midline); top chord = chords[0]
bc, tc = chords[1], chords[0]
bux, buy, bL = unit(bc)
# orient bottom chord: root = the end NEAR the top chord's far end... root = where chords are FAR apart
def perp_sign(c, p):
    ux, uy, L = unit(c)
    return -(p[0]-c['a'][0])*uy + (p[1]-c['a'][1])*ux
d_left = abs(perp_sign(bc, tc['a'])); d_right = abs(perp_sign(bc, tc['b']))
if d_left < d_right:
    bc = {'a': bc['b'], 'b': bc['a'], 'ext': bc['ext'], 'ang': bc['ang']}
    bux, buy, bL = unit(bc)
# now bc['a'] = root end (far from top chord), bc['b'] = tip end
print(f'root at ({bc["a"][0]:.0f},{bc["a"][1]:.0f}), tip at ({bc["b"][0]:.0f},{bc["b"][1]:.0f})')
Z_ROOT, Z_TIP = abs(perp_sign(bc, tc['a'])) * SC, abs(perp_sign(bc, tc['b'])) * SC
print(f'height at root={Z_ROOT:.0f}mm, tip={Z_TIP:.0f}mm')

def xz_of(p):
    """world x along bottom chord from root; z = height above bottom chord line"""
    t = (p[0]-bc['a'][0])*bux + (p[1]-bc['a'][1])*buy
    z = (p[0]-bc['a'][0])*buy - (p[1]-bc['a'][1])*bux   # positive above (y down coords)
    return t * SC, z * SC

members3d = []
for m in member_list:
    p1, p2 = nodes[m['n1']], nodes[m['n2']]
    x1, z1 = xz_of(p1); x2, z2 = xz_of(p2)
    if math.hypot(x2-x1, z2-z1) < 60: continue
    members3d.append({'role': m['role'], 'r_mm': m['r_mm'],
                      'p1': [round(x1,1), 0.0, round(z1,1)],
                      'p2': [round(x2,1), 0.0, round(z2,1)],
                      'rec': m['rec']})
# duplicate to two planes (前/后 ±650, qty=2 约定) + transverse at stations
PLANE = 650.0
final = []
for m in members3d:
    for syn in (1, -1):
        final.append({'role': m['role'] + ('前片' if syn==1 else '后片'),
                      'r_mm': m['r_mm'],
                      'p1': [m['p1'][0], syn*PLANE, m['p1'][2]],
                      'p2': [m['p2'][0], syn*PLANE, m['p2'][2]],
                      'rec': m['rec']})
# transverse frames at chord member nodes (front-back)
node_xs = sorted(set(round(m['p1'][0]) for m in members3d if m['role']=='下弦') )
prev = None
for x in node_xs:
    if prev is not None and x - prev > 300:
        zz = 0.0
        for m in members3d:
            if abs(m['p1'][0]-x) < 60:
                zz = m['p1'][2]; break
        for zl, zh in ((zz, zz),):
            final.append({'role': '横隔(前后片连接)', 'r_mm': 55.0,
                          'p1': [x, -PLANE, zz], 'p2': [x, PLANE, zz], 'rec': {}})
    prev = x
members3d = final
xs = [p['p1'][0] for p in members3d] + [p['p2'][0] for p in members3d]
print(f'3D members: {len(members3d)}, x span {min(xs):.0f}..{max(xs):.0f}')

json.dump({'members': members3d, 'scale': SC},
          open('demo/crossarm008_v1.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('saved demo/crossarm008_v1.json')

# ---------- 4. inject into frame (replace parametric CA1*) ----------
frame = json.load(open('demo/frame.json', encoding='utf-8'))
CA_Z = 114297.0
X_OFF = 2400.0   # 根部(x=0)对齐塔身面
kept = [m for m in frame['members'] if not m['mid'].startswith('R07_') and not m['mid'].startswith('CA1')]
removed = len(frame['members']) - len(kept)
for i, m in enumerate(members3d):
    kept.append({'mid': f'R08_{i:03d}', 'spec': m['role'] + '(008下平面真实几何)',
                 'role': m['role'], 'r_mm': m['r_mm'],
                 'p1': [round(m['p1'][0]+X_OFF,1), round(m['p1'][1],1), round(m['p1'][2]+CA_Z,1)],
                 'p2': [round(m['p2'][0]+X_OFF,1), round(m['p2'][1],1), round(m['p2'][2]+CA_Z,1)]})
frame['members'] = kept
json.dump(frame, open('demo/frame.json','w',encoding='utf-8'), ensure_ascii=False)
print(f'frame: removed {removed} parametric CA1, now {len(kept)} members')

# ---------- 5. render check ----------
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig = plt.figure(figsize=(14, 6))
ax = fig.add_subplot(111, projection='3d')
cols = {'下弦1': 'crimson', '下弦2': 'crimson'}
for m in kept:
    if not (m['mid'].startswith('R08') or m['mid'].startswith('LEG')): continue
    if m['mid'].startswith('LEG') and abs(m['p1'][2]-CA_Z) > 12000: continue
    p1, p2 = m['p1'], m['p2']
    c = 'purple'
    if m['mid'].startswith('R08'):
        c = 'crimson' if '下弦' in m['role'] else ('green' if 'X平面' in m['role'] else 'gray')
    elif m['mid'].startswith('LEG'):
        c = 'green'
    ax.plot([p1[0],p2[0]],[p1[1],p2[1]],[p1[2],p2[2]],color=c,lw=1.0)
ax.view_init(elev=18, azim=-68)
ax.set_box_aspect((2.2, 0.8, 1.2))
plt.savefig('demo/inject008_preview.png', dpi=85)
print('preview saved')
