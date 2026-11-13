from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
docs={
'README.md':'''# LabLedger V2 · 数迹实验数据工坊

面向大学生实验课程、科研入门者和个人作业的本地实验数据管理与统计工具。解决数据散落、清洗覆盖原始值、分析不可复核和报告整理费时的问题。个人参赛作品，参赛者仅一人；不虚构团队、合作单位或人工审核。

## 核心功能与架构

Streamlit界面 → 数据导入/质量检查 → 预览清洗 → SQLite版本保存 → 本地统计与组间对比 → 图表 → 可编辑结论 → 报告ZIP。

- 多实验/多数据集隔离；研究目标、方法、变量、设备、环境、分类、标签与状态。
- 缺失值五种处理、去重、IQR/3σ标记或确认过滤、类型转换、排序筛选、分组均值、标准化、归一化和安全的两列四则派生计算。
- 每次保存保留数据版本、字段定义、操作参数、时间与本地操作者；可恢复历史版本。
- 描述统计、Pearson/Spearman、单/多元线性回归、残差、Welch独立t/配对t/ANOVA适用性检查；移动平均、增长率、滞后自相关。
- 多实验数据集对比、分层条件、均值差、变化率、标准差、箱线图和组间检验。
- 12种高级图表，PNG/SVG/离线交互HTML；原三种图表与仪表盘保留。
- 本地统计证据与可编辑结论；HTML/Markdown/CSV/PNG/ZIP报告；JSON项目迁移、数据库备份恢复和分析快照。

## 技术栈与数据库设计

Python 3.12、Streamlit、SQLite、Pandas、NumPy、Plotly、Matplotlib、SciPy；Pytest与Playwright验证。

projects保存实验及时间，datasets保存所属实验、字段与乐观锁revision，records保留原始文本，dashboards保存布局。V2新增project_meta、versions、history，外键级联清理。Store初始化自动兼容迁移V1并回填已有数据版本，不覆盖原始记录。详细结构见docs/ARCHITECTURE.md。

## 环境与安装

Windows、Python 3.12，建议4GB以上可用内存。PowerShell在项目目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\\install.ps1
powershell -ExecutionPolicy Bypass -File .\\start.ps1
```

浏览器打开 http://127.0.0.1:8501 。首次安装需要网络；已安装依赖后产品完全离线运行。requirements-lock.txt记录此次环境。SciPy缺失时检验显示不可用，其余统计继续工作。

## 使用说明

1. 创建实验，在“实验设置 / 新建数据表”定义字段，或创建算法性能模板表。
2. “数据记录 → CSV导入”预览并确认；替换已有记录需要确认。
3. “实验详情”填写目的和条件；“数据清洗”查看评分，选择操作并预览，点击保存生成新版本。异常默认标记。
4. “专业统计”选择因/自变量并保存快照。“实验对比”选择项目、数据集和条件。
5. “高级图表”选择图形、字段、分组、样式和筛选后下载；“智能分析”编辑并保存草稿。
6. “报告中心”生成并下载完整报告包；“系统设置”查看历史、导出/导入项目、备份/恢复数据库及恢复分析快照。

删除实验需输入完整名称，数据库恢复需显式确认并自动备份当前库。实验无数据时会提示，不生成空报告。

## 演示数据与模板

demo/templates包含物理、化学和算法CSV示例及字段说明。算法种子2026、三种算法、四种规模、每条件10次测量，加入缺失、极端值和一条重复行。

**本数据为软件功能展示用合成数据，不代表真实实验测量结果。** 物理与化学模板同样是合成示例。左侧可一键加载算法演示。

## 存储、安全和测试

通过start.ps1/test.ps1启动，将临时目录、Matplotlib、Streamlit配置、浏览器缓存和测试输出重定向项目D盘；应用也提前设置可配置的临时目录。浏览器手动下载目录由使用者设为exports。SQLite位于data；报告和备份位于exports/v2；不自动清理用户原数据。

CSV和上传上限20MB、限定类型、参数化SQL、导出文件不使用上传文件名、CSV公式前缀转义。报告HTML对文本转义，派生计算不用eval。源码包不含本地用户数据库。

```powershell
powershell -ExecutionPolicy Bypass -File .\\test.ps1
. .\\scripts\\env.ps1
.\\.venv\\Scripts\\python.exe -m pytest -q --basetemp=.runtime/pytest-v2 -o cache_dir=.cache/pytest
.\\.venv\\Scripts\\python.exe scripts/browser_v2.py
```

浏览器验收需要本机Edge、FFmpeg及环回通信权限；录制脚本执行真实UI操作与进程重启。结果见docs/TEST_REPORT_V2.md和reports/browser-v2.json。

## 第三方资源及许可证

见docs/THIRD_PARTY_NOTICES.md、reports/licenses.json；SciPy为BSD-3-Clause并包含第三方数值库声明，完整许可证从安装包提取至docs/SCIPY_LICENSE.txt。系统中文字体、Edge、FFmpeg不随源码分发。源代码授权由真实权利人决定，不擅自指定开源许可证；见LICENSE_NOTICE.md。

## AI工具使用声明

Codex参与需求分析、设计、代码、测试、浏览器操作及文档。产品只使用可解释统计规则，无大模型调用、训练或付费API。参赛者提供需求，后续人工审核、原创贡献和竞赛资格需参赛者自行核实；没有声称本轮AI修改由人工完成。详见docs/AI_USAGE.md。

## 局限性与交付

本地单用户场景，无身份权限、多机同步或大数据增量存储。版本完整保存便于复现，但会增加体积；CSV上限不等于超大表性能保证。常规统计不代替实验设计；正态性检查通过不证明假设成立，多重比较未校正。回归无交叉验证和预测区间，自相关不证明周期。Ollama和PDF导出未集成；报告和图表非分页出版工具。配对检验需唯一配对标识并正确匹配。

V1交付保持不变，V2提交包及SHA256位于交付成果；仅本地Git提交，无远程推送和重新认证。升级细节与未完成项见docs/V2_UPGRADE_REPORT.md；演示脚本见docs/DEMO_SCRIPT_V2.md。
''',
'docs/AI_USAGE.md':'''# V2 AI使用声明

本项目为个人参赛，仅一名参赛者，不存在本报告声称的团队成员或合作单位。

开发阶段：OpenAI Codex实际参与完整需求理解、增量架构设计、Python实现、数据库兼容迁移、测试编写、调试、Playwright真实操作、录制脚本、打包和文档。用户提出需求与约束。未将AI实施的工作虚称为参赛者亲手完成；参赛者尚需审核代码、测试证据、统计解释、授权及竞赛规则并自行讲解。

产品运行阶段：本地统计规则引擎以真实计算结果生成可编辑草稿；不是大语言模型，没有训练模型、虚构AI调用或远程传输。没有集成Ollama，不自动安装或下载模型。全部演示实验数据明确标注为合成，不能用于证明算法真实性能。

本轮无法核实会话以外其他AI工具使用记录，不捏造相关经历。最终竞赛申报需按赛事规定如实披露本声明。
''',
'docs/DEMO_SCRIPT_V2.md':'''# 真实浏览器竞赛演示脚本

目标约3分至3分40秒。画面来自本机Edge真实运行，字幕仅说明当下操作；不是截图拼接。无大模型效果演示。字幕版无配音，可由参赛者现场讲解。

| 阶段 | 操作与说明 |
|---|---|
| 开场 | 首页介绍个人实验工具，展示最近实验与闭环 |
| 创建与导入 | 创建实验、算法模板字段、上传CSV、确认121行；明确合成数据 |
| 清洗 | 解释质量扣分公式、预览去重、保存120行、中位数填补、IQR标记；保留原版本 |
| 统计对比 | 描述统计、回归残差、保存快照；按输入规模100分层比较算法 |
| 图表 | 折线图修改标题，箱线图，热力图；真实下载PNG、SVG、HTML |
| 智能建议 | 显示本地统计证据，编辑草稿与保存，无虚构AI |
| 报告 | 生成HTML/Markdown/CSV/PNG/ZIP，展开正文和图表 |
| 复现 | 下载项目与数据库备份，真实停止并启动第二个服务进程，重新打开历史与版本 |

自动执行：先加载scripts/env.ps1，再运行scripts/browser_v2.py。DEMO_SPEED=0仅用于快速预验收，正式录制不设置此变量。阅读停顿用于展示实际结果，不变速、不循环、不用静态图替代操作。最终精确时长以reports/browser-v2.json和ffprobe实测为准。
''',
'docs/V2_UPGRADE_REPORT.md':'''# V2增量升级报告

2026-11-12，基于V1三次提交，在codex/labledger-v2本地分支升级。初始工作树干净，原测试未删改，旧交付ZIP、视频和清单不覆盖。不访问GitHub认证、不推送远程。

## 实施顺序

审计V1与测试 → SQLite附加表兼容迁移 → 清洗与版本 → 描述统计/回归/检验 → 组间对比 → 高级图表 → 本地证据结论 → 报告与备份 → 页面与浏览器验证 → 文档和独立V2包。

## 新增能力

项目元信息覆盖分类、标签、目标、问题、背景方法、变量、设备环境、备注与状态；多数据集沿用V1隔离设计。附加版本链和历史，不覆盖旧库记录。

清洗包括五种缺失处理、去重、两种异常候选检测、转换排序筛选聚合、缩放与派生列；所有操作先预览再保存。异常过滤要确认。版本包含字段模式，可以恢复新增列之前的版本。

统计覆盖描述统计、成对有效样本相关、多元最小二乘、残差、Welch/配对/ANOVA诊断及本地SciPy降级。实验对比支持选择多个项目的数据集、固定条件分层、差值与波动分析。12种图表具备静态及交互导出。

报告包含来源、质量、版本、统计、适用回归、样本分组、历史对比与结论，完整ZIP带可复现项目。备份和导入保留原版本与分析证据；分析快照可恢复数据及回归选择。

## 限制与尚未完成项

- Ollama为可选需求，本版未集成；不伪造大模型能力。PDF同为可选需求，未实现。
- 统计适用性不替代独立性和实验设计；周期功能仅为自相关线索，阶段对比需选择阶段字段。
- 图表快照保存配置和数据版本，恢复后原配置展示为JSON；不像统计快照那样自动填回全部编辑控件。
- 报告主要按当前数据集生成，保存的跨实验对比作为历史结果纳入；没有完整的多数据集合并排版编辑器。
- 无数据库级多用户权限；删除靠确认防误操作。完整版本快照会增加存储，不适合海量数据。
- 当前无赛事授权信息，源代码许可证由参赛者确定；人工复核与参赛讲解需本人完成。

真实验证状态见TEST_REPORT_V2.md，不将未执行项目写为PASS。
''',
'LICENSE_NOTICE.md':'''# 源代码与资源授权说明

项目源代码权利归真实权利人所有，尚未指定开源授权；本声明不代替权利人授权。竞赛提交前由参赛者确认赛事要求和分发许可。

第三方依赖各自按其许可证使用，见docs/THIRD_PARTY_NOTICES.md、docs/SCIPY_LICENSE.txt及reports/licenses.json。没有分发系统字体、Edge或FFmpeg可执行文件。CSV演示由固定随机种子生成，不包含真实用户数据。
'''
}
for name,content in docs.items(): (ROOT/name).write_text(content,encoding='utf-8')
with (ROOT/'docs/ARCHITECTURE.md').open('a',encoding='utf-8') as out:
    out.write('''\n\n## V2增量结构\n\nproject_meta(project_id,payload)关联研究设计；versions(dataset_id,revision,payload,schema_json,operation,parameters,created_at,actor)保存不可覆盖版本；history(project_id,dataset_id,kind,payload,created_at)保存操作、快照和报告索引。PRAGMA user_version=2，自动回填V1基线。旧表、ID、字段和原始记录保持兼容。保存记录使用revision乐观锁，数据替换、版本与历史在同一事务提交。恢复生成新版本。\n\nscience.py负责有限数值筛选、清洗和统计；advanced_charts.py以Plotly和Matplotlib提供交互及静态导出；reporting.py负责安全HTML、完整ZIP和JSON项目迁移；v2_ui.py只组合界面；runtime.py在应用载入绘图库前重定向可配置缓存。\n\n输入上传不作为路径，CSV防公式注入、20MB限制、报告HTML文本转义、派生四则计算无需eval。备份使用SQLite backup API，恢复先完整性检查并备份当前库。以隔离演示库做浏览器验证；提交包采用允许列表排除data/exports/logs和缓存。\n''')
print('V2 documentation written')
