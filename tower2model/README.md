# tower2model — 输电铁塔图纸 → 三维模型 / 下料清单 / 三视图

把成套铁塔加工图(PDF)变成: 三维模型(OpenSCAD)、拆件下料清单、三视图 PNG、审查报告。
大模型(LLM)可选参与: OCR 明细表行清洗、审查报告润色; 未配置则纯规则模式。

## 快速开始

```bat
pip install -r requirements.txt
run.bat                    (等价于: python -m tower2model run inputs -o outputs)
```

把图纸 PDF(文件名以 `-NNN.pdf` 结尾, 如 `37-SA36901S-T0121-004.pdf`)放进 `inputs\`,跑完在 `outputs\` 拿:

| 产物 | 说明 |
|---|---|
| `views_三视图.png` | 正 / 侧 / 俯 三视图 |
| `render_iso/head/joint.png` | 真实截面渲染(角钢 L 断面 / 空心钢管, 需 OpenSCAD) |
| `tower_frame_real.stl` | 真实截面实体 STL(拆件后坐标, 任意 CAD/3D 打印软件直接打开, 免 OpenSCAD) |
| `frame_fab.json` | 拆件模型(每杆下料坐标 p1t/p2t + 回退量 + 件号) |
| `cut_list.csv` / `bom.csv` | 下料清单 / 材料汇总 |
| `tower_frame.scad` / `tower_frame_real.scad` | 轴线模型 / 真实截面模型 |
| `report.md` | 审查报告(穿透/碰撞/件号覆盖等检查项) |

## 常用命令

```bat
python -m tower2model run inputs -o outputs --gap 3      :: 连接净隙可配
python -m tower2model run inputs --sheets 004,007,013    :: 只 OCR 指定图号(快)
python -m tower2model run inputs --dpi 300               :: OCR 更准(约3倍耗时)
python -m tower2model run inputs --ocr-cache 旧outputs\work\ocr   :: 复用已有OCR
python -m tower2model check outputs\frame_fab.json       :: 只重跑检查
```

## LLM 配置(可选)

`config.yaml`(从 `config.example.yaml` 复制)填 OpenAI 兼容端点:

```yaml
llm_api_base: http://127.0.0.1:8000/v1
llm_api_key: sk-xxx
llm_model: your-model
```

用途: ① OCR 明细表行清洗(修 L 丢失/φ 丢失/数字粘连) ② 审查报告中文润色与风险排序。
不配置时流水线照跑, 报告只含规则检查项。

## OpenSCAD 打包

程序自动按顺序找: `vendor\openscad\openscad.exe` → `C/D:\Program Files\OpenSCAD`。
分发时把本机 OpenSCAD 安装目录整个拷到 `vendor\openscad\` 即可随程序带走(make_release.bat 会自动打进 zip)。

## 适用范围(重要)

几何核心是 **SZK31102A 族参数化重建**(001 正视图为唯一权威: 塔身锥腿+菱形/X 腹杆,
L1 W 形地线支架+W 挂线头, L2/L3 芬克式横担)。同一塔型的全套图纸直接可用;
**新塔型**需要按 `docs` 里的轴线提取流程重建点位表(半自动, 属于逆向工程而非配置项)。

件号覆盖取决于各分段图明细表 OCR 质量, 模型剖分与图纸剖分存在结构性差异
(节点板延伸、X 撑分段), 覆盖率约 40% 属正常, 详见 report.md 说明。
