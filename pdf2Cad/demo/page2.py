# -*- coding: utf-8 -*-
"""Demo v2 page: full-tower frame (Stage A from 001) + workflow + crossarm semantics."""
import json, sys, base64, io
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image

def img64(path, maxw, q=82):
    im = Image.open(path).convert('RGB')
    if im.width > maxw:
        im = im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=q)
    return base64.b64encode(buf.getvalue()).decode()

sheet64 = img64('.superpowers/sp_37-SA36901S-T0121-050.png', 900)
p00164 = img64('.superpowers/p001_overview.png', 830)
frame_prev64 = img64('demo/frame_preview.png', 700)

frame = json.load(open('demo/frame.json', encoding='utf-8'))
frame_js = json.dumps({'members': frame['members'],
                       'profile': frame['profile'],
                       'crossarms': frame['crossarms']}, ensure_ascii=False)

html = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>全塔框架重建 · Demo v2</title>
<style>
body{font-family:'Segoe UI','Microsoft YaHei',sans-serif;background:#0f1420;color:#dde4f0;margin:0;padding:24px}
h1{font-size:22px;margin:0 0 4px}
h2{font-size:17px;color:#7fb2ff;margin:28px 0 10px;border-left:4px solid #3a7bd5;padding-left:10px}
.sub{color:#8a94a8;font-size:13px;margin-bottom:18px}
.grid{display:grid;gap:14px}
.g2{grid-template-columns:1fr 1fr}
.card{background:#171e2e;border:1px solid #26304a;border-radius:10px;padding:14px}
.card h3{margin:0 0 8px;font-size:14px;color:#9fc1ff}
.kpi{font-size:26px;font-weight:700;color:#fff}
.kpis{font-size:12px;color:#8a94a8}
.step{display:flex;gap:10px;align-items:flex-start;margin:8px 0}
.stepn{background:#3a7bd5;color:#fff;border-radius:50%;width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;margin-top:2px}
img{max-width:100%;border-radius:6px;border:1px solid #26304a}
.note{font-size:12px;color:#77819a;line-height:1.6}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;margin-right:6px}
.b-blue{background:#1f2c5a;color:#9ab8ff}.b-green{background:#1f4a24;color:#9affa8}.b-red{background:#5a1f1f;color:#ff9a9a}
button{background:#2a3a5f;color:#cfe0ff;border:1px solid #3a5a8f;border-radius:6px;padding:6px 14px;margin:3px;cursor:pointer;font-size:13px}
button.on{background:#3a7bd5;color:#fff}
#view{width:100%;height:560px;background:#0a0e18;border-radius:8px;cursor:grab;touch-action:none}
#info{font-size:13px;line-height:1.7;color:#c6d2e8}
.dim{color:#77819a}
table{border-collapse:collapse;width:100%;font-size:12px}
th,td{border:1px solid #26304a;padding:3px 6px;text-align:center}
th{background:#1c2740;color:#9fc1ff}
</style>
</head>
<body>
<h1>SZK31102A 135m 双回路直线塔 · 全塔框架重建（Demo v2）</h1>
<div class="sub">按确认的流程重做：<b>001 总图 → 全塔框架 → 逐段按标注细化</b>。本页展示 Stage A 框架成果与横担的正确俯视语义。</div>

<h2>一、两阶段流程（已确认）</h2>
<div class="grid g2">
<div class="card">
  <div class="step"><div class="stepn">1</div><div><b>001 总图 → 全塔框架</b><br>立面轮廓线检测 → 塔身坡度折线（含变坡拐点）→ 标定比例（总高尺寸线 3632pt ↔ 135000mm → 37.17 mm/pt）→ 生成 4 根主材分段 + 横隔 + 交叉斜材 + 横担三角架</div></div>
  <div class="step"><div class="stepn">2</div><div><b>部段图逐张细化</b><br>每张部段图（如 050 横担部段）按其件号标注替换对应框架段杆件：真实规格（Q355φ356X7 等）、真实长度、真实节点构造（法兰/节点板），并跑连接处重合检查</div></div>
  <div class="step"><div class="stepn">3</div><div><b>BOM 对应与导出</b><br>件号 → 明细表行 → 3D 杆件全链路对应，导出 BOM 与 SCAD/CAD</div></div>
</div>
<div class="card">
  <h3>001 总图（识别输入）</h3>
  <img src="data:image/jpeg;base64,__P001__">
  <div class="note" style="margin-top:6px">提取结果：塔身坡度折线 12 个控制点（右表）、4 层横担（顶架 17138 / 上 11401 / 中 11847 / 下 12370 半长）、根开 37560（135m 呼高）。</div>
</div>
</div>

<h2>二、塔身坡度轮廓（自动检测）</h2>
<div class="grid g2">
<div class="card">
<table id="prof"><thead><tr><th>标高 z (mm)</th><th>半宽 (mm)</th><th>含义</th></tr></thead><tbody></tbody></table>
</div>
<div class="card">
  <h3>matplotlib 渲染校验</h3>
  <img src="data:image/jpeg;base64,__FPREV__">
</div>
</div>

<h2>三、Stage A 全塔框架（交互 3D）</h2>
<div class="grid g2">
<div class="card">
  <div><span class="badge b-blue">拖拽旋转 · 滚轮缩放 · 点击杆件</span></div>
  <div style="margin:8px 0">
    <button id="vAll" class="on" onclick="setView('all')">全塔</button>
    <button id="vCA" onclick="setView('ca')">仅横担层</button>
    <button id="vCA0" onclick="focusCA()">聚焦 050 横担 (z=114.3m)</button>
  </div>
  <canvas id="view"></canvas>
</div>
<div class="card">
  <h3>杆件信息</h3><div id="info">点击 3D 杆件查看信息。</div>
  <h3 style="margin-top:14px">050 图的横担语义（纠正后）</h3>
  <img src="data:image/jpeg;base64,__SHEET__">
  <div class="note" style="margin-top:6px">
  050 主视图为<b>横担俯视图</b>：俯视轮廓 = 大三角形（根部宽 2×650 收尖到挂点），即 <b>2 个直角三角形拼合</b>。两根长斜材（2605/2609）为前后两片侧桁架主斜材，在俯视投影中交叉成 X——投影交叉 ≠ 实体交叉（v1 的错误根源）。下弦 2601/2602（L=11847 同规格两根）为前后两片弦杆，投影重合为一根水平线。其余杆件为<b>被截断的延续段</b>或另有详图说明。框架中的横担层 z=114297 即此图对象（半长 11847 ≈ 2601 表长，位置互相印证）。
  </div>
</div>
</div>

<h2>四、产物</h2>
<div class="card">
<div class="step"><div class="stepn">✓</div><div><b>tower_frame.scad</b>（项目根目录 / demo/）— 全塔框架 1:1 mm，OpenSCAD 可直接打开验证尺寸；绿色=主材分段，蓝=横隔，橙=塔身斜材，红=横担</div></div>
<div class="step"><div class="stepn">✓</div><div>218 根杆件全部共节点连接（主材分段点=横隔/斜材端点=横担根部节点）</div></div>
<div class="step"><div class="stepn">→</div><div>下一步：Stage B 细化——把 050 的真实杆件（2601~2623 + 规格）注入 z=114.3m 横担层替换简化三角架，跑重合检查，作为逐段细化的样板</div></div>
</div>

<script>
const FRAME = __FRAME__;
// profile table
const ptb = document.querySelector('#prof tbody');
FRAME.profile.forEach((p,i)=>{
  const tr=document.createElement('tr');
  tr.innerHTML=`<td>${Math.round(p[0])}</td><td>${Math.round(p[1])}</td><td class="dim">${
    i===0?'基底(根开/2)':(i===FRAME.profile.length-1?'塔顶':'塔身变坡控制点')}</td>`;
  ptb.appendChild(tr);
});
// 3D viewer
const cv=document.getElementById('view'), ctx=cv.getContext('2d');
let W,H; function fit(){W=cv.width=cv.clientWidth*devicePixelRatio;H=cv.height=cv.clientHeight*devicePixelRatio;render();}
addEventListener('resize',fit);
let yaw=-0.6,pitch=0.18,dist=1.0,drag=null,selMid=null,viewMode='all';
cv.onmousedown=e=>drag={x:e.clientX,y:e.clientY};
addEventListener('mousemove',e=>{if(!drag)return;yaw+=(e.clientX-drag.x)*0.008;pitch+=(e.clientY-drag.y)*0.008;pitch=Math.max(-1.4,Math.min(1.4,pitch));drag={x:e.clientX,y:e.clientY};});
addEventListener('mouseup',()=>drag=null);
cv.addEventListener('wheel',e=>{e.preventDefault();dist*=e.deltaY>0?1.1:0.9;dist=Math.max(0.2,Math.min(8,dist));},{passive:false});
const CA_Z = 114297, CA_REACH = 11847;
function visible(m){
  if(viewMode==='all') return true;
  return m.mid.startsWith('CA');
}
let ctr=[0,0,67500], span=140000;
function calcBounds(){
  let mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];
  FRAME.members.filter(visible).forEach(m=>[m.p1,m.p2].forEach(p=>{
    for(let i=0;i<3;i++){mn[i]=Math.min(mn[i],p[i]);mx[i]=Math.max(mx[i],p[i]);}}));
  ctr=mn.map((v,i)=>(v+mx[i])/2);
  span=Math.max(mx[0]-mn[0],mx[1]-mn[1],mx[2]-mn[2], 1);
}
function proj(p){
  let x=p[0]-ctr[0],y=p[1]-ctr[1],z=p[2]-ctr[2];
  const cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);
  // yaw rotates in plan (X-Y), Z stays vertical; pitch tilts view up/down
  const rx=x*cy - y*sy;
  const ry=x*sy + y*cy;
  const sy2=z*cp - ry*sp;
  const depth=z*sp + ry*cp;
  const f=(Math.min(W*0.85,H*0.92))/span/dist;
  return [W/2+rx*f, H/2-sy2*f, depth];
}
function cyl(m){
  const a=proj(m.p1),b=proj(m.p2);
  const rpx=Math.max(m.r_mm*(Math.min(W*0.85,H*0.92))/span/dist, 2.5*devicePixelRatio);
  const dx=b[0]-a[0],dy=b[1]-a[1],L=Math.hypot(dx,dy)||1;
  const nx=-dy/L,ny=dx/L;
  let col=['#ffb74d','#a56414'];
  if(m.mid.startsWith('LEG')) col=['#81c784','#2e6b34'];
  else if(m.mid.startsWith('DIA')) col=['#64b5f6','#1a5a8a'];
  if(m.mid.startsWith('CA')&&Math.abs(m.p1[2]-CA_Z)<100) col=['#f06292','#8a1c4a'];
  if(selMid===m.mid) col=['#ff5a7a','#a1123a'];
  ctx.beginPath();
  ctx.moveTo(a[0]+nx*rpx,a[1]+ny*rpx); ctx.lineTo(b[0]+nx*rpx,b[1]+ny*rpx);
  ctx.lineTo(b[0]-nx*rpx,b[1]-ny*rpx); ctx.lineTo(a[0]-nx*rpx,a[1]-ny*rpx); ctx.closePath();
  const g=ctx.createLinearGradient(a[0]+nx*rpx,a[1]+ny*rpx,a[0]-nx*rpx,a[1]-ny*rpx);
  g.addColorStop(0,col[0]);g.addColorStop(0.5,col[1]);g.addColorStop(1,col[0]);
  ctx.fillStyle=g;ctx.fill();
  return {m,a,b,rpx};
}
function render(){
  if(!cv.clientWidth) return;
  ctx.fillStyle='#0a0e18';ctx.fillRect(0,0,W,H);
  calcBounds();
  const ms=FRAME.members.filter(visible);
  const items=ms.map(cyl);
  items.sort((p,q)=>q.a[2]+q.b[2]-(p.a[2]+p.b[2]));
  window._items=items;
}
function pick(ev){
  const r=cv.getBoundingClientRect();
  const x=(ev.clientX-r.left)*devicePixelRatio,y=(ev.clientY-r.top)*devicePixelRatio;
  let best=null,bd=1e9;
  (window._items||[]).forEach(({m,a,b,rpx})=>{
    const dx=b[0]-a[0],dy=b[1]-a[1],L2=dx*dx+dy*dy||1;
    let t=((x-a[0])*dx+(y-a[1])*dy)/L2;t=Math.max(0,Math.min(1,t));
    const d=Math.hypot(x-(a[0]+dx*t),y-(a[1]+dy*t))-rpx;
    if(d<bd){bd=d;best=m;}
  });
  return bd<8*devicePixelRatio?best:null;
}
cv.addEventListener('click',e=>{
  const m=pick(e);
  selMid=m?m.mid:null;
  document.getElementById('info').innerHTML=m?
    `<b>${m.mid}</b> · ${m.role}<br>规格：${m.spec}<br>`+
    `P1 (${m.p1.map(v=>Math.round(v)).join(', ')})<br>P2 (${m.p2.map(v=>Math.round(v)).join(', ')})`:
    '点击 3D 杆件查看信息';
  render();
});
function setView(v){
  viewMode=v;
  ['vAll','vCA','vCA0'].forEach(id=>document.getElementById(id).classList.remove('on'));
  document.getElementById(v==='all'?'vAll':v==='ca'?'vCA':'vCA0').classList.add('on');
  if(v==='ca'){yaw=-0.6;pitch=0.6;dist=0.5;}
  render();
}
function focusCA(){
  setView('all');
  // frame the z=114.3m crossarm level
  viewMode='ca2';
  window.visible=m=>Math.abs(m.p1[2]-CA_Z)<2000||Math.abs(m.p2[2]-CA_Z)<2000||m.mid.startsWith('LEG');
  ctr=[0,0,CA_Z+900];
  span=CA_REACH*2.8;
  yaw=0.5;pitch=0.5;dist=1.0;
  render();
}
// wrap visible
const _vis=visible;
visible=m=>window._vOverride?window._vOverride(m):_vis(m);
fit();
</script>
</body>
</html>"""

html = html.replace('__P001__', p00164).replace('__FPREV__', frame_prev64).replace('__SHEET__', sheet64)
html = html.replace('__FRAME__', frame_js)

import os
out1 = r'F:\workspace\orca\brainStorm\pdf2Cad\.superpowers\brainstorm\20464-1789617705\content\demo2.html'
open(out1, 'w', encoding='utf-8').write(html)
out2 = r'F:\workspace\orca\brainStorm\pdf2Cad\demo2.html'
open(out2, 'w', encoding='utf-8').write(html)
print('written', f'{os.path.getsize(out1)/1024:.0f} KB x2')
