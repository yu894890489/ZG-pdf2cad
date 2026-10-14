# -*- coding: utf-8 -*-
"""tower2model Web 服务(零新依赖, 纯标准库)
浏览器上传图纸 PDF -> 服务器跑 tower2model 流水线 -> 下载 STL/bom.csv/cut_list.csv + STL 在线 3D 预览

启动: python webapp/server.py   (或双击 start_web.bat)
"""
import os, sys, io, re, json, uuid, time, queue, threading, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))                     # webapp/
PROJ = os.path.dirname(BASE)                                          # brainStorm/
ROOT = os.path.join(PROJ, 'tower2model')                              # 项目根(含 tower2model 包)
sys.path.insert(0, ROOT)
JOBS_DIR = os.path.join(BASE, 'jobs')
STATIC_DIR = os.path.join(BASE, 'static')
PORT = int(os.environ.get('T2M_PORT', '8000'))

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
# 预 import: 让模块顶部的 stdout.reconfigure 在真实 stdout 上执行完再替换
import tower2model.pipeline as pipeline
import tower2model.render  # noqa

JOBS = {}          # jid -> dict
JOBQ = queue.Queue()

WORKER = threading.Thread(target=lambda: _worker(), daemon=True)


def _safe_name(name):
    name = os.path.basename(name.replace('\\', '/'))
    name = re.sub(r'[^\w\.\-一-鿿() ]', '_', name)
    return name.strip() or 'file'


def _worker():
    while True:
        jid = JOBQ.get()
        job = JOBS.get(jid)
        if not job:
            continue
        jdir = os.path.join(JOBS_DIR, jid)
        inp, out = os.path.join(jdir, 'inputs'), os.path.join(jdir, 'outputs')
        job['status'] = 'running'
        logbuf = _JobLog(job)
        old = sys.stdout
        sys.stdout = logbuf
        try:
            stats = pipeline.run(inp, out, gap=job['gap'])
            job['status'] = 'done'
            job['files'] = _list_outputs(out)
            job['parse_mode'] = (stats or {}).get('parse_mode', '')
        except Exception as e:
            job['status'] = 'error'
            job['error'] = f'{e}\n\n{traceback.format_exc()}'
            print(f'\n[错误] {e}')
        finally:
            sys.stdout = old
        job['t1'] = time.time()


def _list_outputs(out):
    files = []
    if os.path.isdir(out):
        for n in sorted(os.listdir(out)):
            p = os.path.join(out, n)
            if os.path.isfile(p) and not (n.endswith('.scad') and '_view_' in n):
                files.append({'name': n, 'size': os.path.getsize(p)})
    return files


class _JobLog(io.TextIOBase):
    def __init__(self, job):
        self.job = job

    def write(self, s):
        if s:
            self.job['log'] = (self.job.get('log', '') + s)[-12000:]
        return len(s)

    def flush(self):
        pass

    def reconfigure(self, **kw):  # 兜底
        pass

    def isatty(self):
        return False


def _parse_multipart(body, boundary):
    """返回 (fields, files); files=[(filename, bytes)]"""
    fields, files = {}, []
    delim = b'--' + boundary
    for part in body.split(delim)[1:]:
        if part in (b'--', b'--\r\n', b''):
            continue
        part = part.lstrip(b'\r\n')
        head, sep, data = part.partition(b'\r\n\r\n')
        if not sep:
            continue
        if data.endswith(b'\r\n'):
            data = data[:-2]
        m = re.search(rb'name="([^"]*)"(?:; filename="([^"]*)")?', head)
        if not m:
            continue
        name = m.group(1).decode('utf-8', 'replace')
        fname = m.group(2).decode('utf-8', 'replace') if m.group(2) else None
        if fname:
            files.append((fname, data))
        else:
            fields[name] = data.decode('utf-8', 'replace')
    return fields, files


PAGE = """<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>铁塔图纸建模服务</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><text y='14' font-size='14'>🗼</text></svg>">
<style>
:root{--bd:#d8dee6;--fg:#1c2733;--dim:#6a7686;--ac:#0f6bff}
*{box-sizing:border-box}
body{margin:0;font:15px/1.6 "Microsoft YaHei",system-ui,sans-serif;color:var(--fg);background:#f4f6f9}
.wrap{max-width:860px;margin:0 auto;padding:24px 16px 60px}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--dim);font-size:13px;margin-bottom:20px}
.card{background:#fff;border:1px solid var(--bd);border-radius:10px;padding:18px;margin-bottom:16px}
.drop{border:2px dashed #b9c4d0;border-radius:8px;padding:22px;text-align:center;color:var(--dim);cursor:pointer}
.drop.on{border-color:var(--ac);background:#f0f6ff}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:12px}
button{background:var(--ac);color:#fff;border:0;border-radius:6px;padding:9px 22px;font-size:15px;cursor:pointer}
button:disabled{background:#9db9e0;cursor:not-allowed}
input[type=number]{width:90px;padding:7px;border:1px solid var(--bd);border-radius:6px}
.badge{display:inline-block;padding:2px 10px;border-radius:10px;font-size:12px;color:#fff}
.st-queued{background:#8a94a3}.st-running{background:#d9822b}.st-done{background:#2e8b57}.st-error{background:#c23b3b}
.log{background:#10161d;color:#9fd3a0;font:12px/1.5 Consolas,monospace;padding:12px;border-radius:8px;
     max-height:260px;overflow:auto;white-space:pre-wrap;margin:10px 0}
table{width:100%;border-collapse:collapse;font-size:14px}
td,th{padding:7px 8px;border-bottom:1px solid #edf0f4;text-align:left}
a.dl{color:var(--ac);text-decoration:none;font-weight:600}
.hint{color:var(--dim);font-size:13px}
.err{color:#c23b3b;font-size:13px;white-space:pre-wrap}
.job{margin-bottom:14px}
</style></head><body><div class=wrap>
<h1>铁塔图纸三维建模服务</h1>
<div class=sub>上传成套加工图 PDF(文件名如 37-SA36901S-T0121-004.pdf)→ 自动生成三维模型 STL、材料表 BOM、下料清单</div>

<div class=card>
  <div class=drop id=drop>点击选择 或 拖拽图纸 PDF 到此处(可多选)<br><span class=hint>仅支持 *.pdf</span>
    <input id=file type=file multiple accept=.pdf hidden></div>
  <div class=row>
    <span>连接净隙 gap(mm):<input type=number id=gap value=3 min=0 step=0.5></span>
    <button id=go disabled>开始建模</button>
    <span class=hint id=pick></span>
  </div>
</div>

<div id=jobs></div>
<div class=hint>服务端自动排队处理;OCR 识别约 40~60 秒/张,请勿关闭页面。</div>
</div>
<script>
const jobsEl=document.getElementById('jobs');
const fileIn=document.getElementById('file'),drop=document.getElementById('drop'),
      go=document.getElementById('go'),pick=document.getElementById('pick');
let picked=[];
drop.onclick=()=>fileIn.click();
fileIn.onchange=()=>setPicked([...fileIn.files]);
drop.ondragover=e=>{e.preventDefault();drop.classList.add('on')};
drop.ondragleave=()=>drop.classList.remove('on');
drop.ondrop=e=>{e.preventDefault();drop.classList.remove('on');setPicked([...e.dataTransfer.files])};
function setPicked(fs){picked=fs.filter(f=>/\\.pdf$/i.test(f.name));
  go.disabled=!picked.length;
  pick.textContent=picked.length?picked.length+' 个文件: '+picked.map(f=>f.name).join(', '):'已忽略非 PDF 文件'}
go.onclick=()=>{
  const fd=new FormData();
  picked.forEach(f=>fd.append('files',f));
  fd.append('gap',document.getElementById('gap').value||3);
  go.disabled=true;pick.textContent='上传中...';
  fetch('/api/run',{method:'POST',body:fd}).then(r=>r.json()).then(j=>{
    if(j.id)addJob(j.id);else alert('上传失败: '+(j.error||''));
  }).catch(e=>alert('上传失败: '+e)).finally(()=>{go.disabled=false;pick.textContent='';fileIn.value='';picked=[]});
};
const ST={queued:'排队中',running:'建模中',done:'完成',error:'失败'};
function addJob(id){
  const card=document.createElement('div');card.className='card job';card.id='job-'+id;
  jobsEl.prepend(card);poll(id,card);save();
}
function poll(id,card){
  fetch('/api/status?id='+id).then(r=>r.json()).then(j=>{
    render(card,j);
    if(j.status==='queued'||j.status==='running')setTimeout(()=>poll(id,card),1500);
    else save();
  }).catch(()=>setTimeout(()=>poll(id,card),3000));
}
function render(card,j){
  const el=j.status==='done'?fmtE(j.t1-j.t0):'';
  const PM={builtin:'',llm:'LLM 解析',llm_partial:'LLM 解析·部分',vector_only:'矢量解析·结果不可靠',fallback_default:'降级兜底·结果不可靠'};
  const pm=j.parse_mode?PM[j.parse_mode]||j.parse_mode:'';
  card.innerHTML='<div class=row><b>任务 '+j.id.slice(0,8)+'</b>'+
    '<span class="badge st-'+j.status+'">'+ST[j.status]+'</span>'+
    (pm?'<span class=badge style="background:#fff3cd;color:#856404">'+pm+'</span>':'')+
    '<span class=hint>'+(j.nfiles?j.nfiles+' 张图纸':'')+' '+el+'</span></div>'+
    (j.log?'<div class=log id=log></div>':'')+
    (j.error?'<div class=err>'+esc(j.error)+'</div>':'')+
    (j.files?fileTable(j):'');
  const lg=card.querySelector('.log');if(lg){lg.textContent=j.log;lg.scrollTop=lg.scrollHeight}
}
function fmtE(s){return '耗时 '+Math.round(s)+' 秒'}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;')}
function fileTable(j){
  let h='<table><tr><th>产物文件</th><th>大小</th><th></th></tr>';
  j.files.forEach(f=>{
    const dl='/api/download?job='+j.id+'&file='+encodeURIComponent(f.name);
    h+='<tr><td>'+esc(f.name)+'</td><td class=hint>'+(f.size/1024).toFixed(0)+' KB</td><td>';
    if(/\\.stl$/i.test(f.name))h+='<a class=dl href="/view?job='+j.id+'&file='+encodeURIComponent(f.name)+'" target=_blank>3D 预览</a> &nbsp; ';
    if(/\\.(png|md)$/i.test(f.name))h+='<a class=dl href="'+dl+'" target=_blank>查看</a> &nbsp; ';
    h+='<a class=dl href="'+dl+'" download="'+esc(f.name)+'">下载</a></td></tr>';
  });
  return h+'</table>';
}
function save(){const ids=[...document.querySelectorAll('.job')].map(e=>e.id.slice(4));
  localStorage.setItem('t2m_jobs',JSON.stringify(ids.slice(0,10)))}
(function restore(){try{const ids=JSON.parse(localStorage.getItem('t2m_jobs')||'[]');
  ids.reverse().forEach(id=>{const c=document.createElement('div');c.className='card job';c.id='job-'+id;
  jobsEl.appendChild(c);poll(id,c)})}catch(e){}})();
</script></body></html>"""

VIEW_PAGE = """<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>STL 三维预览</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#1a2230;font:13px "Microsoft YaHei",sans-serif}
#bar{position:fixed;top:10px;left:12px;color:#cfe0ff;z-index:9;text-shadow:0 1px 3px #000}</style>
</head><body><div id=bar>加载中…(左键旋转 / 滚轮缩放 / 右键平移)</div>
<script src="/static/three.min.js"></script>
<script src="/static/OrbitControls.js"></script>
<script src="/static/STLLoader.js"></script>
<script>
const q=new URLSearchParams(location.search);
document.title='3D 预览 - '+q.get('file');
const scene=new THREE.Scene();scene.background=new THREE.Color(0x1a2230);
scene.add(new THREE.HemisphereLight(0xdfeaff,0x334055,1.05));
const sun=new THREE.DirectionalLight(0xffffff,0.9);sun.position.set(1,-0.6,1.4);scene.add(sun);
const fill=new THREE.DirectionalLight(0xbfd4ff,0.4);fill.position.set(-1,0.5,-0.8);scene.add(fill);
const camera=new THREE.PerspectiveCamera(50,innerWidth/innerHeight,1,3000000);
const renderer=new THREE.WebGLRenderer({antialias:true});
renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(devicePixelRatio);
document.body.appendChild(renderer.domElement);
const grid=new THREE.GridHelper(100000,40,0x3a4a63,0x27344a);grid.rotation.x=Math.PI/2;scene.add(grid);
const controls=new THREE.OrbitControls(camera,renderer.domElement);
camera.up.set(0,0,1);controls.update();
(function animate(){requestAnimationFrame(animate);controls.update();renderer.render(scene,camera)})();
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();
  renderer.setSize(innerWidth,innerHeight)});
fetch('/api/download?job='+q.get('job')+'&file='+encodeURIComponent(q.get('file')))
.then(r=>{if(!r.ok)throw new Error(r.status);return r.arrayBuffer()})
.then(buf=>{
  const geo=new THREE.STLLoader().parse(buf);
  geo.computeVertexNormals();
  const mesh=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({color:0xc9d3dd,metalness:0.15,roughness:0.4,side:THREE.DoubleSide}));
  scene.add(mesh);
  geo.computeBoundingBox();
  const box=geo.boundingBox,c=new THREE.Vector3();box.getCenter(c);
  const s=box.getSize(new THREE.Vector3()).length();
  mesh.position.set(-c.x,-c.y,-c.z);
  grid.scale.setScalar(s/120000);grid.position.set(0,0,box.min.z-c.z);
  camera.near=s/2000;camera.far=s*30;camera.updateProjectionMatrix();
  const d=s*1.15;
  camera.position.set(d*0.22,-d*0.88,d*0.45);controls.target.set(0,0,0);controls.update();
  document.getElementById('bar').textContent='三维尺寸: '+Math.round(box.max.x-box.min.x)+' x '+
    Math.round(box.max.y-box.min.y)+' x '+Math.round(box.max.z-box.min.z)+' mm';
})
.catch(e=>document.getElementById('bar').textContent='STL 加载失败: '+e);
</script></body></html>"""

CT = {'.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css',
      '.png': 'image/png', '.pdf': 'application/pdf', '.stl': 'model/stl',
      '.csv': 'text/csv; charset=utf-8', '.json': 'application/json', '.md': 'text/markdown; charset=utf-8',
      '.scad': 'text/plain; charset=utf-8'}


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        pass  # 安静模式

    # ---------- helpers ----------
    def _send(self, code, body, ctype='text/html; charset=utf-8', extra=None):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        self._send(200, json.dumps(obj, ensure_ascii=False).encode('utf-8'),
                   'application/json; charset=utf-8')

    def _redirect_html(self):
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    # ---------- GET ----------
    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == '/':
                return self._send(200, PAGE.encode('utf-8'))
            if u.path == '/view':
                return self._send(200, VIEW_PAGE.encode('utf-8'))
            if u.path.startswith('/static/'):
                fn = _safe_name(u.path[len('/static/'):])
                p = os.path.join(STATIC_DIR, fn)
                if os.path.isfile(p):
                    with open(p, 'rb') as f:
                        return self._send(200, f.read(),
                                          CT.get(os.path.splitext(fn)[1], 'application/octet-stream'),
                                          {'Cache-Control': 'max-age=86400'})
                return self._send(404, b'not found')
            if u.path == '/api/ping':
                return self._json({'ok': True, 'jobs': len(JOBS),
                                   'busy': any(j['status'] == 'running' for j in JOBS.values())})
            if u.path == '/api/status':
                jid = (q.get('id') or [''])[0]
                job = JOBS.get(jid)
                if not job:
                    return self._json({'status': 'unknown'})
                d = {k: job.get(k) for k in ('status', 'log', 'files', 'error', 't0', 't1', 'nfiles', 'parse_mode')}
                d['id'] = jid
                return self._json(d)
            if u.path == '/api/download':
                jid = (q.get('job') or [''])[0]
                fn = _safe_name((q.get('file') or [''])[0])
                p = os.path.join(JOBS_DIR, jid, 'outputs', fn)
                if not (jid and os.path.isfile(p)):
                    return self._send(404, b'not found')
                with open(p, 'rb') as f:
                    data = f.read()
                from urllib.parse import quote
                ext = os.path.splitext(fn)[1]
                # 图片/报告直接浏览器内打开, 其余触发下载
                disp = 'inline' if ext.lower() in ('.png', '.md', '.pdf') else 'attachment'
                ascii_fn = fn.encode('ascii', 'replace').decode().replace('"', '')
                return self._send(200, data,
                                  CT.get(ext, 'application/octet-stream'),
                                  {'Content-Disposition':
                                   f"{disp}; filename=\"{ascii_fn}\"; filename*=UTF-8''{quote(fn)}"})
            return self._send(404, b'not found')
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ---------- POST ----------
    def do_POST(self):
        u = urlparse(self.path)
        try:
            if u.path != '/api/run':
                return self._send(404, b'not found')
            if any(j['status'] == 'running' for j in JOBS.values()):
                return self._json({'error': '已有任务在建模中,请稍候再提交'})
            ln = int(self.headers.get('Content-Length') or 0)
            if ln <= 0 or ln > 500 * 1024 * 1024:
                return self._json({'error': '请求体为空或超过 500MB'})
            body = self.rfile.read(ln)
            ct = self.headers.get('Content-Type', '')
            m = re.search(r'boundary=([^;]+)', ct)
            if not m:
                return self._json({'error': '缺少 boundary'})
            fields, files = _parse_multipart(body, m.group(1).strip('"').encode())
            pdfs = [(n, d) for n, d in files if n.lower().endswith('.pdf') and d]
            if not pdfs:
                return self._json({'error': '没有收到 PDF 文件'})
            jid = uuid.uuid4().hex[:16]
            jdir = os.path.join(JOBS_DIR, jid)
            os.makedirs(os.path.join(jdir, 'inputs'), exist_ok=True)
            for n, d in pdfs:
                with open(os.path.join(jdir, 'inputs', _safe_name(n)), 'wb') as f:
                    f.write(d)
            JOBS[jid] = {'status': 'queued', 'log': '', 'files': None, 'error': '',
                         't0': time.time(), 't1': None, 'nfiles': len(pdfs),
                         'gap': float(fields.get('gap') or 3) or 3.0}
            JOBQ.put(jid)
            print(f'[任务] {jid} 收到 {len(pdfs)} 张图纸, gap={JOBS[jid]["gap"]}')
            return self._json({'id': jid, 'nfiles': len(pdfs)})
        except Exception as e:
            traceback.print_exc()
            return self._json({'error': str(e)})


def _lan_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


if __name__ == '__main__':
    os.makedirs(JOBS_DIR, exist_ok=True)
    WORKER.start()
    ip = _lan_ip()
    print(f'=' * 56)
    print(f'  铁塔图纸建模服务已启动')
    print(f'  本机访问:   http://127.0.0.1:{PORT}/')
    print(f'  局域网访问: http://{ip}:{PORT}/   (同事电脑浏览器打开)')
    print(f'  任务与产物保存在: {JOBS_DIR}')
    print(f'  Ctrl+C 停止服务')
    print(f'=' * 56)
    ThreadingHTTPServer.allow_reuse_address = False  # Windows 防止端口被二次绑定
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
