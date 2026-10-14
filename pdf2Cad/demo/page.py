# -*- coding: utf-8 -*-
"""Assemble the self-contained demo HTML page and push to the visual companion server."""
import json, sys, base64, io
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image

# ---- assets ----
def img64(path, maxw, q=82):
    im = Image.open(path).convert('RGB')
    if im.width > maxw:
        im = im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=q)
    return base64.b64encode(buf.getvalue()).decode()

sheet64 = img64('.superpowers/sp_37-SA36901S-T0121-050.png', 900)
axes64 = img64('demo/axes_overlay.png', 1100)
table64 = img64('.superpowers/t050_table.png', 700)

model = json.load(open('demo/members.json', encoding='utf-8'))

BOM = [
 ['2601','Q355φ356X7','11847','4','713.76','2855.0',''],
 ['2602','Q355φ356X7','11847','4','713.76','2855.0',''],
 ['2603','Q355φ356X7','2854','4','171.95','687.8',''],
 ['2604','Q355-14X554','1430','4','87.06','348.2',''],
 ['2605','Q355φ299X6','10185','2','883.2','1766.4',''],
 ['2606','Q355φ299X6','8785','2','380.87','1523.5',''],
 ['2607','Q355φ356X7','1927','2','116.10','237.2',''],
 ['2608','Q355φ356X7','11400','2','686.83','1373.7',''],
 ['2609','Q355φ273X5','9234','4','305.15','1220.6',''],
 ['2610','Q355-12X473','1430','4','63.72','254.9',''],
 ['2611','Q355-14X490','686','2','53.26','213.0',''],
 ['2612','Q355-12X365','871','4','29.95','119.8',''],
 ['2613','Q355-12X326','289','2','8.87','35.5',''],
 ['2614','Q355-14X300','270','2','9.07','36.3',''],
 ['2615','Q355-14X300','385','2','12.69','50.8',''],
 ['2616','Q355-12X436','1284','4','52.74','211.0',''],
 ['2617','Q355-10X80','754','8','4.74','37.9',''],
 ['2618','Q355-10X80','754','8','4.74','37.9',''],
 ['2619','Q355-10X576','636','2','28.86','115.4',''],
 ['2620','Q355-10X100','160','8','1.26','10.1','拉索附件'],
 ['2621','Q355-8X50','100','8','0.31','2.5','拉索附件切角'],
 ['2622','Q355-10X72','72','4','0.41','1.6',''],
 ['2623','Q355-10X50','35','4','0.14','0.6',''],
 ['GJ-50','拉索','24920','4','10.47','41.9','拉索附件'],
 ['NUT-2','螺母','','4','3.20','12.8','拉索附件'],
 ['U-10','','','4','0.60','2.4','拉索附件'],
 ['NX-2.1','','','4','2.40','9.6','拉索附件'],
 ['JK-2','','','8','0.32','2.6','拉索附件'],
 ['C2705H5','法兰','','8','15.10','144.8',''],
 ['C2906H5','法兰','','8','23.31','186.5',''],
 ['C3507H5','法兰','','12','36.27','435.2',''],
 ['FD2929B7H','法兰','','8','15.70','125.6',''],
 ['FD3535B7H','法兰','','20','22.10','442.0',''],
 ['合计','','','','','15393.0 kg',''],
]

bom_js = json.dumps(BOM, ensure_ascii=False)
model_js = json.dumps(model, ensure_ascii=False)

html = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>PDF图纸→3D铁塔建模 可行性Demo</title>
<style>
body{font-family:'Segoe UI','Microsoft YaHei',sans-serif;background:#0f1420;color:#dde4f0;margin:0;padding:24px}
h1{font-size:22px;margin:0 0 4px}
h2{font-size:17px;color:#7fb2ff;margin:28px 0 10px;border-left:4px solid #3a7bd5;padding-left:10px}
.sub{color:#8a94a8;font-size:13px;margin-bottom:18px}
.grid{display:grid;gap:14px}
.g4{grid-template-columns:repeat(4,1fr)}
.g2{grid-template-columns:1fr 1fr}
.card{background:#171e2e;border:1px solid #26304a;border-radius:10px;padding:14px}
.card h3{margin:0 0 8px;font-size:14px;color:#9fc1ff}
.kpi{font-size:26px;font-weight:700;color:#fff}
.kpis{font-size:12px;color:#8a94a8}
.step{display:flex;gap:10px;align-items:flex-start;margin:8px 0}
.stepn{background:#3a7bd5;color:#fff;border-radius:50%;width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;margin-top:2px}
img{max-width:100%;border-radius:6px;border:1px solid #26304a}
table{border-collapse:collapse;width:100%;font-size:12px}
th,td{border:1px solid #26304a;padding:3px 6px;text-align:center}
th{background:#1c2740;color:#9fc1ff;position:sticky;top:0}
td.hl{background:#3a5a2a;color:#c8ff9a;font-weight:700}
.scroll{max-height:340px;overflow-y:auto}
#view{width:100%;height:480px;background:#0a0e18;border-radius:8px;cursor:grab;touch-action:none}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;margin-right:6px}
.b-red{background:#5a1f1f;color:#ff9a9a}.b-green{background:#1f4a24;color:#9affa8}.b-blue{background:#1f2c5a;color:#9ab8ff}.b-gray{background:#333c50;color:#aab4c8}
button{background:#2a3a5f;color:#cfe0ff;border:1px solid #3a5a8f;border-radius:6px;padding:6px 14px;margin:3px;cursor:pointer;font-size:13px}
button.on{background:#3a7bd5;color:#fff}
#info{font-size:13px;line-height:1.7;color:#c6d2e8}
.note{font-size:12px;color:#77819a;line-height:1.6}
.dim{color:#77819a}
</style>
</head>
<body>
<h1>PDF 图纸 → 三维铁塔模型 · 可行性验证 Demo</h1>
<div class="sub">样本：SZK31102A 双回路直线钢管塔 · 图纸 37-SA36901S-T0121-050（横担部段图，矢量PDF，文字转曲）· 全流程仅用本次提取的数据驱动</div>

<h2>一、流水线各环节产出</h2>
<div class="grid g4">
  <div class="card"><h3>① 矢量提取</h3><div class="kpi">2,272</div><div class="kpis">几何线段（精确坐标）<br>+992 文字簇 · 68 件号圈</div></div>
  <div class="card"><h3>② OCR 识别</h3><div class="kpi">308 条</div><div class="kpis">全图文字 · 平均置信度 0.90<br>数字/规格/中文表头均命中</div></div>
  <div class="card"><h3>③ 明细表解析</h3><div class="kpi">33 行</div><div class="kpis">构件+附件 · 合计 15,393.0 kg<br>编号↔规格↔长度↔数量↔重量</div></div>
  <div class="card"><h3>④ 3D 重建+检查</h3><div class="kpi">6 → 0</div><div class="kpis">连接处干涉：初模 6 处<br>平面分配+相贯修剪后 0 处</div></div>
</div>

<h2>二、图纸 → 结构化数据</h2>
<div class="grid g2">
  <div class="card"><h3>原始图纸（050 横担部段图）</h3><img src="data:image/jpeg;base64,__SHEET__"></div>
  <div class="card"><h3>矢量线分类：蓝图=提取线段 · 红/绿/橙=识别出的竖/横/斜构件轴线</h3><img src="data:image/jpeg;base64,__AXES__"><div class="note" style="margin-top:8px">斜材双轮廓线自动配对成中心线；比例用"表长11847mm ↔ 提取长度1179pt"标定（≈10.05 mm/pt）；构件旁的法兰构造（650|650 尺寸）确定了前后片平面间距 ±650mm。</div></div>
</div>

<h2>三、构件明细表 = BOM 源数据（OCR + 网格解析 + 符号纠正）</h2>
<div class="grid g2">
  <div class="card"><h3>图纸原表（150dpi 截取）</h3><img src="data:image/jpeg;base64,__TABLE__"></div>
  <div class="card"><h3>解析结果（悬停行可在 3D 中定位演示杆件）</h3>
  <div class="scroll"><table id="bom"><thead><tr><th>编号</th><th>规格</th><th>长度mm</th><th>数量</th><th>单重kg</th><th>共重kg</th><th>备注</th></tr></thead><tbody></tbody></table></div>
  <div class="note" style="margin-top:8px">OCR 原始输出 "0355#356X7" → 纠正为 "Q355φ356X7"（工程符号后处理规则）。</div></div>
</div>

<h2>四、3D 杆系模型 + 连接处重合检查（交互）</h2>
<div class="grid g2">
<div class="card">
  <div>
    <span class="badge b-blue">拖拽旋转 · 滚轮缩放 · 点击杆件查看信息</span>
  </div>
  <div style="margin:8px 0">
    <button id="b1" onclick="setStage(1)">S1 初模(2D直接拉伸)</button>
    <button id="b2" onclick="setStage(2)">S2 前后片平面分配</button>
    <button id="b3" class="on" onclick="setStage(3)">S3 相贯修剪后</button>
  </div>
  <canvas id="view"></canvas>
  <div class="note" style="margin-top:8px">模型仅含本视图中有直接证据的 <b>6 根杆件</b>（明细表中的 2602 为投影重合推定件，未纳入）。可导出验证：<b>demo/tower_050.scad</b>（OpenSCAD 格式，1:1 mm，含件号/规格/表长注释），在 OpenSCAD 中打开即可核对尺寸。</div>
</div>
<div class="card">
  <h3>杆件信息</h3><div id="info">点击左侧 3D 杆件查看：件号、规格、表长 vs 模型长、所属明细表行。</div>
  <h3 style="margin-top:14px">连接检查结果 <span id="stageTag" class="badge b-green">S3</span></h3>
  <div id="collist" class="scroll" style="max-height:260px"></div>
</div>
</div>
<div class="card" style="margin-top:14px">
<h3>本 demo 验证了什么 / 没验证什么</h3>
<div class="grid g2">
<div>
<div class="step"><div class="stepn">✓</div><div>矢量 PDF 精确提取几何与表格——比扫描件路线可靠一个量级</div></div>
<div class="step"><div class="stepn">✓</div><div>文字转曲图 OCR 可达工程可用精度（0.90），工程符号可规则纠正</div></div>
<div class="step"><div class="stepn">✓</div><div>件号→明细表→3D 杆件 全链路对应（BOM 追溯可行）</div></div>
<div class="step"><div class="stepn">✓</div><div>连接处重合可自动检测并自动修正（平面分配+相贯修剪），剩余项自动转人工清单</div></div>
</div>
<div>
<div class="note">待正式设计确认的问题：① 全塔 165 张图的批量拓扑重建（本 demo 为单张 5~7 杆件）；② 杆件前后片归属目前由法兰构造推定，正式版应从断面图自动读取；③ 节点板/螺栓级细节不在 Mode A 范围；④ 字形聚类字典可作为 OCR 的离线增强（建一次全项目复用）。</div>
</div>
</div>
</div>

<script>
const MODEL = __MODEL__;
const BOM = __BOM__;
// ---------- BOM table ----------
const tb = document.querySelector('#bom tbody');
BOM.forEach((r,i)=>{
  const tr=document.createElement('tr');
  if(r[0]==='合计'){tr.innerHTML=`<td colspan="5" style="text-align:right;font-weight:700">合计</td><td class="hl">${r[5]}</td><td></td>`;}
  else{tr.innerHTML=r.map(c=>`<td>${c}</td>`).join('');}
  tr.dataset.i=i;
  if(['2601','2602','2605','2606','2607','2608','2609'].includes(r[0])){
    tr.style.cursor='pointer';
    tr.onmouseenter=()=>highlightByCallout(r[0]);
    tr.onmouseleave=()=>highlightByCallout(null);
  }
  tb.appendChild(tr);
});
// ---------- 3D ----------
const cv=document.getElementById('view'), ctx=cv.getContext('2d');
let W,H; function fit(){W=cv.width=cv.clientWidth*devicePixelRatio;H=cv.height=cv.clientHeight*devicePixelRatio;}
fit(); addEventListener('resize',fit);
let yaw=-0.5,pitch=0.35,dist=1.0,drag=null, selMid=null, stage=3, hovCallout=null;
cv.onmousedown=e=>drag={x:e.clientX,y:e.clientY};
addEventListener('mousemove',e=>{if(!drag)return;yaw+=(e.clientX-drag.x)*0.008;pitch+=(e.clientY-drag.y)*0.008;pitch=Math.max(-1.4,Math.min(1.4,pitch));drag={x:e.clientX,y:e.clientY};});
addEventListener('mouseup',()=>drag=null);
cv.addEventListener('wheel',e=>{e.preventDefault();dist*=e.deltaY>0?1.1:0.9;dist=Math.max(0.5,Math.min(6,dist));},{passive:false});
// model bounds
let mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];
MODEL.stages.s3.members.forEach(m=>[m.p1,m.p2].forEach(p=>{for(let i=0;i<3;i++){mn[i]=Math.min(mn[i],p[i]);mx[i]=Math.max(mx[i],p[i]);}}));
const ctr=mn.map((v,i)=>(v+mx[i])/2), span=Math.max(mx[0]-mn[0],mx[1]-mn[1],mx[2]-mn[2]);
function proj(p){
  let x=p[0]-ctr[0],y=p[1]-ctr[1],z=p[2]-ctr[2];
  const cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);
  let x1=x*cy+z*sy, z1=-x*sy+z*cy, y1=y*cp-z1*sp, z2=y*sp+z1*cp;
  const f=(Math.min(W*0.85, H*0.92))/span/dist;
  const s=dist*span;
  const k=f/(1+ (z2/s)*0.0);  // orthographic-ish
  return [W/2+x1*k, H/2-y1*k, z2];
}
function cyl(m){
  const a=proj(m.p1),b=proj(m.p2);
  const rpx=Math.max(m.r_mm*(Math.min(W*0.85,H*0.92))/span/dist, 5*devicePixelRatio);
  const dx=b[0]-a[0],dy=b[1]-a[1],L=Math.hypot(dx,dy)||1;
  const nx=-dy/L,ny=dx/L;
  const sel = selMid===m.mid || (hovCallout===m.callout);
  let col;
  if(m.callout==='2601'||m.callout==='2602') col=['#4fc3f7','#0b6e9e'];
  else if(m.callout==='2607'||m.callout==='2608') col=['#aed581','#4e7a2a'];
  else col=['#ffb74d','#a56414'];
  if(sel) col=['#ff5a7a','#a1123a'];
  // body quad
  ctx.beginPath();
  ctx.moveTo(a[0]+nx*rpx,a[1]+ny*rpx); ctx.lineTo(b[0]+nx*rpx,b[1]+ny*rpx);
  ctx.lineTo(b[0]-nx*rpx,b[1]-ny*rpx); ctx.lineTo(a[0]-nx*rpx,a[1]-ny*rpx); ctx.closePath();
  const g=ctx.createLinearGradient(a[0]+nx*rpx,a[1]+ny*rpx,a[0]-nx*rpx,a[1]-ny*rpx);
  g.addColorStop(0,col[0]);g.addColorStop(0.5,col[1]);g.addColorStop(1,col[0]);
  ctx.fillStyle=g;ctx.fill();
  // end caps
  for(const [p,q] of [[a,b],[b,a]]){
    const t=[(q[0]-p[0]),(q[1]-p[1])];const L2=Math.hypot(t[0],t[1])||1;
    const ex=t[0]/L2,ey=t[1]/L2;
    ctx.beginPath();ctx.ellipse(p[0],p[1],rpx,rpx*0.35,Math.atan2(ey,ex),0,Math.PI*2);
    ctx.fillStyle=col[1];ctx.fill();
  }
  // label
  if(rpx>4){
    const mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2;
    ctx.fillStyle='#fff';ctx.font=`${11*devicePixelRatio}px sans-serif`;ctx.textAlign='center';
    ctx.fillText(m.callout,mx,my-6);
  }
  return {m,a,b,rpx};
}
function render(){
  ctx.clearRect(0,0,W,H);
  ctx.fillStyle='#0a0e18';ctx.fillRect(0,0,W,H);
  // ground grid
  const ms=MODEL.stages['s'+stage].members;
  const items=ms.map(cyl);
  items.sort((p,q)=>q.a[2]+q.b[2]-(p.a[2]+p.b[2]));
  // collisions overlay
  const its=MODEL.stages['s'+stage].items;
  const colMap={};
  its.forEach(it=>{if(it.type==='干涉'){it.pair.forEach(id=>colMap[id]=true);}});
  ctx.globalAlpha=1;
  items.forEach(it=>cyl(it.m));
  // draw collision markers
  its.filter(i=>i.type==='干涉').forEach(it=>{
    const m1=ms.find(x=>x.mid===it.pair[0]),m2=ms.find(x=>x.mid===it.pair[1]);
    const p1=m1.p1,p2=m1.p2;
    const px=proj([(p1[0]+p2[0])/2,(p1[1]+p2[1])/2,(p1[2]+p2[2])/2]);
    ctx.beginPath();ctx.arc(px[0],px[1],7*devicePixelRatio,0,7);
    ctx.fillStyle='#ff2d2d';ctx.fill();
    ctx.fillStyle='#fff';ctx.font=`${10*devicePixelRatio}px sans-serif`;ctx.textAlign='center';
    ctx.fillText(it.pen+'mm',px[0],px[1]+3*devicePixelRatio);
  });
  // click hit-test storage
  window._items=items;
}
function pick(ev){
  const r=cv.getBoundingClientRect();
  const x=(ev.clientX-r.left)*devicePixelRatio,y=(ev.clientY-r.top)*devicePixelRatio;
  let best=null,bd=1e9;
  (window._items||[]).forEach(({m,a,b,rpx})=>{
    // distance point to segment
    const dx=b[0]-a[0],dy=b[1]-a[1],L2=dx*dx+dy*dy||1;
    let t=((x-a[0])*dx+(y-a[1])*dy)/L2;t=Math.max(0,Math.min(1,t));
    const px=a[0]+dx*t,py=a[1]+dy*t;
    const d=Math.hypot(x-px,y-py)-rpx;
    if(d<bd){bd=d;best=m;}
  });
  return bd<8*devicePixelRatio?best:null;
}
cv.addEventListener('click',e=>{
  const m=pick(e);
  selMid=m?m.mid:null;
  if(m){
    document.getElementById('info').innerHTML=
     `<b>件号 ${m.callout}</b> · ${m.role}<br>规格：${m.spec}（半径 ${m.r_mm.toFixed(0)}mm）<br>`+
     `表长：${m.table_L.toFixed(0)} mm ｜ 模型可见段长：${m.L_model_mm.toFixed(0)} mm${m.table_L?'<br><span class=dim>可见段≠表长：该杆件延续到相邻图（跨视图），正式版按全塔拓扑拼接</span>':''}`+
     (m.cope&&m.cope.length?`<br>相贯修剪于：${m.cope.join('、')}`:'');
  } else {
    document.getElementById('info').textContent='点击左侧 3D 杆件查看信息';
  }
  render();
});
function highlightByCallout(co){hovCallout=co;render();}
function collist(){
  const its=MODEL.stages['s'+stage].items;
  const el=document.getElementById('collist');
  const tags={干涉:'b-red',接触:'b-green',校核:'b-gray'};
  el.innerHTML=its.length?its.map(it=>
    `<div style="margin:6px 0"><span class="badge ${tags[it.type]}">${it.type}</span> ${it.callouts.join(' × ')} ${it.pen?`<b style="color:#ff9a9a">${it.pen}mm</b> `:''}<span class="dim">${it.why}</span></div>`
  ).join(''):'<div class="note">无</div>';
}
function setStage(s){
  stage=s;
  [1,2,3].forEach(i=>document.getElementById('b'+i).classList.toggle('on',i===s));
  const tag=document.getElementById('stageTag');
  const its=MODEL.stages['s'+s].items;
  const n=its.filter(i=>i.type==='干涉').length;
  tag.textContent=`S${s} · 干涉 ${n} 处`;
  tag.className='badge '+(n===0?'b-green':n>4?'b-red':'b-blue');
  collist();render();
}
setStage(3);
</script>
</body>
</html>"""

html = html.replace('__SHEET__', sheet64).replace('__AXES__', axes64).replace('__TABLE__', table64)
html = html.replace('__MODEL__', model_js).replace('__BOM__', bom_js)

out = r'F:\workspace\orca\brainStorm\pdf2Cad\.superpowers\brainstorm\320-1789608544\content\demo.html'
open(out, 'w', encoding='utf-8').write(html)
import os
print('written', out, f'{os.path.getsize(out)/1024:.0f} KB')
