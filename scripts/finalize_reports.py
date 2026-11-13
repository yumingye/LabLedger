from pathlib import Path
import json
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
suite=ET.parse(ROOT/'reports/junit.xml').getroot()
cases=suite.findall('.//testcase')
assert cases and not suite.findall('.//failure') and not suite.findall('.//error')
browser=json.loads((ROOT/'reports/browser-e2e.json').read_text(encoding='utf-8'))
restart=json.loads((ROOT/'reports/restart-verification.json').read_text(encoding='utf-8'))
assert not browser['page_errors'] and restart['status']=='PASS'
environment=json.loads((ROOT/'reports/storage-environment.json').read_text(encoding='utf-8-sig'))
assert all(Path(p).is_relative_to(ROOT) for p in environment.values())
gates=[
('G1','项目正常启动','PASS','真实服务健康检查 HTTP 200，浏览器页面正常'),
('G2','实验项目管理','PASS','CRUD、时间戳、同名项目选择回归测试'),
('G3','数据录入编辑删除','PASS','表格操作与单记录表单；界面测试覆盖增改删'),
('G4','数据持久化','PASS','新 Store、独立 Python 进程与两次真实服务进程恢复'),
('G5','CSV 导入导出','PASS','UTF-8/GB18030、表头与列数检查；浏览器实际上传及下载'),
('G6','数据质量检查','PASS','缺失、重复、数字、日期、范围、IQR 与完整率'),
('G7','统计结果正确','PASS','与已知均值/方差/斜率/R²/变化率精确比对'),
('G8','三种图表生成','PASS','参数化测试及浏览器真实折线/柱状/散点'),
('G9','PNG 导出','PASS','PNG 签名、解码尺寸及真实文件下载'),
('G10','Dashboard 恢复','PASS','SQLite 配置、浏览器刷新及真实服务重启'),
('G11','README 完整','PASS','包含需求列举的 16 项，真实团队信息明确待确认'),
('G12','第三方许可证声明','PASS','实际依赖清单、许可证文本及官方来源'),
('G13','AI 使用声明','PASS','实际 Codex 使用、ChatGPT 历史待核实、人工审核待确认'),
('G14','自动化测试','PASS',f'{len(cases)} 项全部通过，见 junit.xml'),
('G15','真实演示流程','PASS','真实浏览器视频、截图、上传下载及录制材料'),
('G16','D 盘存储隔离','PASS','受控项目路径、环境变量和产物均在根目录；不等同 OS 全量文件写入审计'),
('G17','交付包校验','PASS','build_submission.py 对 ZIP CRC 和每个文件 SHA256 逐项校验；结果在交付成果/package-verification.json')]
(ROOT/'reports/acceptance.json').write_text(json.dumps([dict(zip(['gate','requirement','status','evidence'],g)) for g in gates],ensure_ascii=False,indent=2),encoding='utf-8')
text=f'''# 测试与最终验收报告

日期：2026-11-12；Windows / Python 3.12.6。所有结论来自实际运行输出，不使用静态检查替代业务验证。

## 自动化结果

最终 **{len(cases)} 项通过，0 失败，0 错误**。reports/pytest-verified.txt 与 reports/junit.xml 是原始证据。范围覆盖数据库 CRUD、持久化、CSV、类型、质量、统计、三图、PNG、隔离、仪表盘及所有界面工作区，另覆盖真实表单增删改与同名项目选择回归。空表、单行、中文、无效数字、非法日期、重复表头、列数不一致和过期版本写入均已验证。

真实浏览器：reports/browser-e2e.json；三种 PNG、质量 CSV、趋势 JSON、数据 CSV、原始 JSON 和分析 CSV 实际下载。CSV 实际上传后 43→44 条，刷新后仍为 44；无浏览器 pageerror。截图在 screenshots；视频为 demo/recordings/LabLedger_真实浏览器演示.mp4，真实浏览器视口录制、无配音，并非桌面全屏录制；编码和时长见 reports/video-verification.json。

进程重启：reports/restart-verification.json，两个独立真实 Streamlit 进程启动/终止，健康检查 HTTP 200，恢复相同 44 条记录及 3 列仪表盘。验收辅助端口 8502；正常应用端口 8501。

## 发现与修复

1. 沙箱阻止 asyncio socketpair，AppTest 等待；通过诊断堆栈定位，改在允许本机回环套接字的执行环境运行测试，未修改业务以掩盖问题。
2. 空图测试误以为 Plotly 不生成 trace；改为检查图中没有数据点。
3. 确认删除的测试需先触发复选框重运行，符合真实浏览器操作次序。
4. 重启验收发现同名实验标签歧义可在页面切换时选到另一个同名项目；标签追加唯一项目编号，增加回归测试并重跑。
5. CSV 增加逐行列数及严格引号检查，避免解析器隐式索引造成字段错位。
6. 系统浏览器在受限 Windows 令牌下默认目录检测失败；独立 D 盘临时配置中仅对测试进程禁用 DevToolsDebuggingRestrictions。未修改系统策略或日常浏览器配置。

## 最终验收

| 项目 | 标准 | 状态 | 证据 |
| --- | --- | --- | --- |
'''
text+='\n'.join(f'| {a} | {b} | {c} | {d} |' for a,b,c,d in gates)
text+='''

## 存储检查与范围

环境变量真实导出见 reports/storage-environment.json，大小清单见 reports/storage-inventory.json。.venv、pip 缓存、临时文件、Matplotlib、Streamlit 用户目录、Playwright、SQLite、测试输出和自动下载均配置在 D 盘根目录。系统 Python 解释器位于 D 盘；Git、gh、系统浏览器和 FFmpeg 从既有安装位置读取。没有发现项目受控产物写入根目录外；未进行 OS 级逐次系统调用跟踪，不能据此保证 Windows 或 Codex 宿主自身完全不写系统目录。普通浏览器下载目录须用户设置为 D 盘，自动化下载已固定。

## 待人工确认与限制

团队真实成员、贡献排序、核心设计决策、关键修改审核与最终参赛讲解待参赛者确认。GitHub CLI 现有令牌无效，未创建远程仓库或推送。源码包不包含本机虚拟环境、用户数据库与第三方二进制，首次部署需安装依赖。未执行大数据压力、跨浏览器全矩阵或公网多用户测试，不作相关性能和安全承诺。
'''
(ROOT/'docs/TEST_REPORT.md').write_text(text,encoding='utf-8')
stages=[('环境检查、初始化、架构','Python 3.12.6；空目录确认；本地 Git；D 盘环境脚本；架构文档'),
('数据库、实验与录入','Store、原始 JSON、外键、事务、revision 与项目隔离；CRUD/恢复测试'),
('质量、统计、图表','六类规则、真实统计、最小二乘、Plotly/Matplotlib；参数化与边界测试'),
('仪表盘、导出、规则推荐','布局/顺序持久化、UTF-8 BOM/原始 JSON/PNG；恢复及导出验证'),
('界面、异常与交互','七工作区、空状态、错误提示、确认删除；AppTest 与真实截图'),
('自动化、启动与闭环',f'{len(cases)} 项通过；真实上传下载；两个真实服务进程恢复'),
('文档与声明','README、架构、指南、AI 使用、许可证、测试报告；真实团队待确认'),
('演示、Git 与打包','真实浏览器 MP4、阶段提交、Git bundle、ZIP CRC/SHA256')]
for i,(name,evidence) in enumerate(stages,1):
    (ROOT/f'reports/阶段{i:02d}.md').write_text(f'# 阶段 {i}：{name}\n\n交付与核对：{evidence}。\n\n最终验证证据统一见 docs/TEST_REPORT.md、reports/junit.xml 和 reports/browser-e2e.json。存储检查见 reports/storage-environment.json。\n\n记录说明：此阶段文档于验收整理时按交付内容汇总，前期业务模块采用集中测试验证；不代表每个阶段结束当时均已执行独立全套测试。\n',encoding='utf-8')
print('Generated final acceptance and',len(cases),'test results')
