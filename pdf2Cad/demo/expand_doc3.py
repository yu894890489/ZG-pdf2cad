# -*- coding: utf-8 -*-
"""第四轮补充"""
import io
path = 'demo/gen_doc.py'
src = io.open(path, encoding='utf-8').read()

# 3.2 阶段接口表
src = src.replace(
    "P('构件描述 JSON 核心字段契约（节选）：', bold=True)",
    "P('阶段间接口约定：', bold=True)\n"
    "TBL(['接口', '生产者→消费者', '内容'],\n"
    "    [['sheet_index', 'S1→全部', '图纸号、幅面、路径数、缩略图索引'],\n"
    "     ['block_list', 'S1→S2', '图块类型（全局/大样/明细表）、裁剪框、矢量要素包'],\n"
    "     ['part_json', 'S2→S3', '构件描述 JSON（含置信度）'],\n"
    "     ['part_json_verified', 'S3→S4', '校验与标准化后的构件 JSON（含复核标记）'],\n"
    "     ['model_3d', 'S4→S5/S6/S7', '杆系模型（节点+杆件+截面+连接）'],\n"
    "     ['discrepancy_report', 'S6→S7', '闭合差/干涉/矛盾清单（定位到图纸区域）'],\n"
    "     ['data_pair', 'S7→训练库', '专家确认数据对（修改前后差值）']])\n"
    "P('构件描述 JSON 核心字段契约（节选）：', bold=True)", 1)

# 5.2 字段表
src = src.replace(
    "H(2, '5.3  人机协同工作台')",
    "P('构件 JSON 主要字段：', bold=True)\n"
    "TBL(['字段', '类型', '说明'],\n"
    "    [['part_id', 'string', '件号（图纸内唯一）'],\n"
    "     ['type', 'enum', 'tube/angle/plate/flange/bolt/guy'],\n"
    "     ['spec', 'string', '标准化规格（Q355φ219X6 等）'],\n"
    "     ['length', 'number', '下料长度 mm'],\n"
    "     ['qty', 'number', '数量'],\n"
    "     ['unit_weight', 'number', '单重 kg'],\n"
    "     ['nodes', 'array', '端部节点及连接方式（螺栓/焊接/法兰）'],\n"
    "     ['source', 'object', '来源图纸号、视图、区域坐标（溯源用）'],\n"
    "     ['confidence', 'number', '解析置信度 0~1'],\n"
    "     ['review_flag', 'bool', '是否需人工复核']])\n"
    "H(2, '5.3  人机协同工作台')", 1)

# 8.3 社会效益
src = src.replace(
    "H(1, '附录 A  前期原理验证（POC）实测数据摘要')",
    "H(2, '8.3  社会效益')\n"
    "P('本项目将铁塔深化设计从\"个人经验驱动\"转变为\"系统与数据驱动\"，降低了对稀缺深化设计师的依赖，有助于缓解行业人才瓶颈；图纸错误的前置拦截可减少现场返工与安全隐患，间接提升电网工程建设质量；系统沉淀的图纸理解数据资产亦可为电网工程数字化（如数字孪生运维）提供基础数据。')\n"
    "H(1, '附录 A  前期原理验证（POC）实测数据摘要')", 1)

# 附录B 术语补行
src = src.replace(
    "     ['数据飞轮', '人工复核数据沉淀→模型微调→精度提升→复核减少的正向循环']])",
    "     ['数据飞轮', '人工复核数据沉淀→模型微调→精度提升→复核减少的正向循环'],\n"
    "     ['LoRA', '低秩适配（Low-Rank Adaptation），大模型轻量微调技术'],\n"
    "     ['JSON Schema', 'JSON 数据结构约束规范，用于强制大模型输出合规格式'],\n"
    "     ['放样大样图', '工厂下料用的单件二维加工图']])")

io.open(path, 'w', encoding='utf-8').write(src)
print('expanded v4 done')
