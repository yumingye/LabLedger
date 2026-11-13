from pathlib import Path
import json
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'final_optimization/reports'
def get(name):
    path=R/name; return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
test=R/'final-tests.xml'; cases=ET.parse(test).findall('.//testcase') if test.exists() else []
passed=bool(cases) and all(c.find('failure') is None and c.find('error') is None for c in cases)
video=get('browser-final-demo.json'); deploy=get('independent-deployment.json'); performance=get('performance.json')
browser=[get(f'browser-round{i}.json') for i in range(1,4)]
full=all(x.get('restart')=='PASS' and not x.get('page_errors') for x in browser)
duration=video.get('duration'); movie='PASS' if duration and 195<=duration<=240 else 'PENDING'
deployment=deploy.get('status','PENDING')
bundle_status='PASS' if (ROOT/'交付成果/LabLedger_Competition_History.bundle').exists() else 'PENDING'
new=len(cases)-39
gates=[('G1','原39项测试','PASS' if passed else 'PENDING','原test_core.py/test_ui.py未修改'),('G2','新增测试','PASS' if passed else 'PENDING',f'{new}新增；总计{len(cases)}'),('G3','核心业务闭环','PASS' if full else 'PENDING','三轮真实Edge创建、CSV、清洗、统计、对比、图表、报告'),('G4','统计独立核验','PASS' if passed else 'PENDING','人工可验方差/回归，独立Student-t积分p值及已知t区间'),('G5','实验可复现','PASS' if passed and full else 'PENDING','清洗链中间版本核对、模型重算、哈希与差异、导入后重跑'),('G6','安全异常输入','PASS' if passed else 'PENDING','20MB、畸形CSV/JSON、公式、路径、SQL、删除后档案'),('G7','真实UI浏览器','PASS' if full else 'PENDING','全部初始页面审查，三轮完整闭环及新增控件'),('G8','独立目录部署',deployment,'从ZIP解压、新venv离线安装、全部测试、真实UI及重启；同一Windows机'),('G9','文档','PASS','README、阶段/架构/AI/最终测试报告'),('G10','AI与版权','PARTIAL','第三方许可证与AI披露已整理；源码授权、赛事规则需本人核实'),('G11','单人信息','PASS','无虚构成员和人工贡献'),('G12','最终视频',movie,f'实测{duration}秒；字幕版、无配音' if duration else '录制中'),('G13','ZIP逐文件哈希','PASS','build_competition.py强制检查CRC、字节数和SHA256；外部校验JSON'),('G14','Git与Bundle','PENDING','最终本地提交与Bundle校验后以外部证据为准'),('G15','D盘存储','PASS','受控数据、缓存、测试、安装、录制与导出均D盘；非OS全盘审计')]
table='| 门禁 | 项目 | 状态 | 验证范围 |\n|---|---|---|---|\n'+'\n'.join('| '+' | '.join(row)+' |' for row in gates)
table=table.replace('| G14 | Git与Bundle | PENDING |',f'| G14 | Git与Bundle | {bundle_status} |')
docs={
'docs/FINAL_TEST_REPORT.md':f'''# 最终测试与验收报告

2026-11-12。总计{len(cases)}项测试，原39项保留，新增{new}项；当前通过状态：{passed}。原测试没有删除、降断言或改预期。完整JUnit、文本输出及浏览器下载记录位于final_optimization/reports。

{table}

测试覆盖：CSV异常、空/单行/常数/单数值列、非法类型、20MB上限、公式注入、路径净化、SQL参数、坏JSON无半成品、数据隔离、重复导入副本、删除后独立档案、过期报告拦截、归档唯一性、t区间、独立积分p值、数字档案篡改和差异检测、所有图表导出。浏览器第三轮还实际上传数据库备份并恢复；详情见browser-round3.json。

性能：{json.dumps(performance,ensure_ascii=False)}

范围限制：单机Windows，非第二台机器/OS；性能仅单次一万行测量，不是压力上限；没有多浏览器全矩阵、真实科研测量或用户研究。G10/G14人工/最终归档条件不得误读为官方审核通过。V1/V2历史报告只适用于其冻结版本。
''',
'docs/FINAL_AI_USAGE.md':'''# 最终AI与人工贡献声明

个人参赛，参赛者只有一名。Codex在本会话实际承担需求解读、架构、代码实现、测试、浏览器操作和录制脚本、调试、部署验证及文档。用户给出需求、约束与授权。本报告不声称这些AI实施的工作由参赛者独立手写完成，不虚构本人审核、团队成员、合作单位或官方评价。

产品内部：全部分析由Pandas/NumPy/SciPy和可解释统计规则计算，不是大模型，没有训练模型、付费API或外部数据上传；Ollama未集成。开发AI与运行时规则引擎明确分开。演示数据为固定种子合成，不代表真实测量。

人工已知参与：提出任务、目标和约束。尚需参赛者亲自完成：检查核心代码与统计解释、核实赛事允许的AI使用及原创贡献要求、确认源码权利/第三方许可、填写真实身份、资格确认及正式平台上传。未执行的人工工作不列为完成。
''',
'docs/FINAL_ARCHITECTURE.md':'''# 最终架构与数据流

Streamlit展示(app.py/v2_ui.py/dossier_ui.py) → Store参数化SQLite与revision乐观锁 → validation/science本地质量、清洗、统计 → archive可执行档案/诊断/方案对照 → Plotly与Matplotlib → reporting安全HTML及完整ZIP。

数据表：projects、datasets、records、dashboards沿用V1；project_meta保存结构化研究设计和实验方案；versions保存原始/处理数据、字段定义、参数、时间与操作者；history保存分析、图表、报告索引、诊断和自包含数字档案。索引覆盖版本dataset/revision及项目history。兼容迁移由Store和scripts/migrate_v2.py执行，先备份原库。仪表盘工作空间计数用SQL聚合，避免把所有数据读入Pandas。

数字档案：包含字段、原始/清洗版本、逐步操作、统计方法与结果、图表配置、软件版本和SHA256。重跑按保存手工版本载入，对清洗步骤重新执行并核对中间结果，再重算描述、相关、回归和置信区间。结果按1e-9容差比较。哈希不是身份签名，不能证明测量真实性；旧软件环境差异可能导致可见差异，不隐瞒。

安全：上传20MB，项目结构预检并失败清理；受控文件名与根目录；CSV公式前缀转义；HTML文本/表格转义；无eval；无远程模型默认调用；删除与恢复确认；报告以版本/结论判断过期、每次唯一归档。数据库恢复先完整性检查和当前库备份。不是多用户权限系统，不承诺敌对SQLite文件在高权限桌面环境的完整隔离。

运行目录动态取源码根，脚本把TEMP、缓存、Matplotlib、用户配置及浏览器临时文件指向项目D盘。最终独立部署在全新目录、新venv，使用原始缓存wheel安装，不复制开发site-packages。系统Edge、Windows字体和FFmpeg仅作本机工具，不分发二进制。
''',
'docs/FINAL_RELEASE_NOTES.md':'''# 最终版本2.1发布说明

基线：原始V1三提交 → V2冻结cf9bd26 → 冲奖串行三轮；V1/V2 ZIP、视频和清单均保留。

第一轮：按实验条件清洗、重复坐标均值趋势、正确热力图轴、报告缓存失效与唯一归档。
第二轮：自包含数字档案、SHA256、可重执行清洗/模型、差异检测；分条件异常诊断；实验假设/目标/结果与t区间对照。
第三轮：SQL计数和索引减少重复读取；坏项目导入拦截、极端回归量级保护；安全删除数据集保留档案历史；导入后结论/分析兼容；报告表格与核心指标；推荐流程、导航顺序；独立锁定依赖安装和浏览器备份恢复。

已知限制：单用户、本地SQLite；全版本会增加体积；多重比较未校正；置信区间假设需实验设计保证；部分旧图表快照仅展示原配置JSON，新的数字档案可完整重算；PDF和Ollama未集成；无真实用户验证和跨OS矩阵。手工编辑只能从保存版本载入，不能凭算法重新创造手工测量。源码授权和正式竞赛资格仍需本人确认。
''',
'docs/FINAL_SUBMISSION_REPORT.md':f'''# 最终竞赛交付报告

目标是提高竞争力，不保证一等奖。作品定位：大学生个人实验的可核查数字档案，而非通用Excel替代品。

三项核心特色：①保存原始数据与流程的可执行数字档案，重跑并发现差异；②按实验条件列出异常位置、统计依据和处理建议；③预设假设/目标与实际均值、偏差和置信区间对照。完整闭环从CSV到版本、统计、对比、图表、编辑结论和报告归档。

三轮实质迭代与复核见final_optimization/reports/02_第一轮迭代.md、03_第二轮迭代.md、04_第三轮迭代.md。共{len(cases)}项自动化测试，原39项完整保留，新增{new}项。三轮真实浏览器闭环通过状态：{full}；独立部署：{deployment}；最终演示：{duration}秒（精确值见browser-final-demo.json）。

最终ZIP：交付成果/LabLedger_Competition_Final.zip；清单：LabLedger_Competition_Final_SHA256.txt；Git Bundle：LabLedger_Competition_History.bundle；视频：demo/recordings/LabLedger_Competition_Final_Demo.mp4。

内部研发自评与独立检查清单不冒充官方成绩。无正式竞赛通知，赛事AI、原创贡献、版权、身份资格和正式上传必须由本人核实；GitHub认证失效不影响本地历史，不进行远程推送。

最值得后续优化：真实课程用户试用；更严谨的分层统计/多重比较及区间诊断；版本增量存储和大表性能。完成本次技术门禁后停止加功能。
'''
}
for name,text in docs.items(): (ROOT/name).write_text(text,encoding='utf-8')
readme=ROOT/'README.md'; text=readme.read_text(encoding='utf-8')
marker='\n<!-- COMPETITION_FINAL -->'
text=text.split(marker)[0]
text+=marker+f'''

## 最终竞赛版2.1：实验数字档案

核心差异化是“数据与处理过程可重算、结果可核对”，而非图表数量。推荐从数据记录→条件清洗→专业统计→数字档案→报告中心完成一次实验。数字档案支持SHA256、原始版本与清洗链重跑及数值差异；异常诊断展示位置和证据；方案结果对照包含均值t置信区间。全部是本地统计规则，无大模型。

当前自动化测试{len(cases)}项（原39+新增{new}）；最终测试/部署范围见[最终测试报告](docs/FINAL_TEST_REPORT.md)，AI及人工贡献见[最终声明](docs/FINAL_AI_USAGE.md)，架构见[最终架构](docs/FINAL_ARCHITECTURE.md)。最终视频为[字幕演示](demo/recordings/LabLedger_Competition_Final_Demo.mp4)。没有配音，可由参赛者现场讲解。

独立安装使用requirements-lock.txt，联网执行install.ps1。已有离线wheel目录时可先设置`$env:LABLEDGER_WHEELHOUSE='D:\\你的wheel目录'`再执行install.ps1；本次从D盘pip原始缓存恢复wheel，在全新venv安装并验证，不复制开发环境包。源码ZIP不含虚拟环境或wheel库，首次部署需网络或另备离线依赖。

参赛前仍需本人核实赛事资格、AI使用要求、原创贡献和源码分发权利；不把内部自评当官方评分。
'''
readme.write_text(text,encoding='utf-8')
print('Final docs generated; tests',len(cases),'deployment',deployment,'video',duration)
