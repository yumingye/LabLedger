# 数迹实验数据工坊 · LabLedger

面向大学生实验课程与科研入门的个人本地实验工作台。它把实验记录、数据质检、统计分析、图表和可复验档案放在同一条工作流中。本次更新沿用原有 LabLedger 2.1 的功能，增加表格自动保存以及与图表配置关联的 PNG 和 CSV 导出。

## 功能

- 实验与数据集管理，数字、文本、日期字段，表格自动保存、CSV 导入、搜索筛选和导出。
- 数据完整率、重复、类型、范围和 IQR 异常提示。清洗预览、版本历史、恢复及统计趋势并存。
- 折线、柱状和散点图，支持坐标字段、标题、分组、字体、字号、尺寸、配色、图例、网格和轴标题。
- 图表可下载双倍像素 PNG 及有效坐标 CSV。另可在导出中心下载原始数据和统计结果。
- SQLite 保存数据、清洗版本、图表仪表盘与实验历史。可封存数字档案并重跑分析，导出报告或备份。

## 安装、启动和测试

使用 Windows、PowerShell 和 Python 3.12，在 D 盘此仓库的根目录运行以下命令。脚本将虚拟环境、数据库、日志和其他运行产物放入项目内部。首次安装需要联网，离线安装可用环境变量 LABLEDGER_WHEELHOUSE 指向完整的锁定依赖 wheel 目录。

~~~powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
powershell -ExecutionPolicy Bypass -File .\start.ps1
~~~

打开 [本机工作台](http://127.0.0.1:8501)。关闭终端前用 Ctrl+C 停止程序，重启读取同一个 data/labledger.sqlite3。可用 LABLEDGER_DB 指定另一个项目内的数据库。

~~~powershell
powershell -ExecutionPolicy Bypass -File .\test.ps1
~~~

## 演示流程

在左栏新建实验，打开「实验设置 / 新建数据表」并创建默认数据表。从「数据记录」导入课堂示例，在质量中心检查提示，返回录入页逐字段修改一个数值并观察自动保存反馈。进入「图表工坊」，调整样式并下载 PNG 和图表数据 CSV。重启后打开同一实验核对保存的数据。示例数据用于验证软件行为。[课堂示例](demo/competition_sample.csv) · [1080p 真实浏览器演示](demo/LabLedger_自动保存与导出.mp4)

## 技术与材料

Python、Streamlit、SQLite、Pandas、NumPy、SciPy、Plotly 和 Matplotlib。界面调用领域服务与 SQLite 存储层，数据版本与历史采用事务维护。自动化采用 Pytest、Streamlit AppTest 与 Playwright。

- [架构](docs/ARCHITECTURE.md) · [使用手册](docs/USER_GUIDE.md) · [开发说明](docs/DEVELOPMENT.md) · [测试报告](docs/TEST_REPORT.md) · [演示脚本](docs/DEMO_SCRIPT.md)
- [原创授权](LICENSE_NOTICE.md) · [第三方资源及许可](docs/THIRD_PARTY_NOTICES.md) · [AI 工具使用](docs/AI_USAGE.md)
- 本作品按个人参赛管理。OpenAI Codex 参与审计、设计、开发、验证和文档，运行时分析使用本地统计规则。参赛者审核与实质改动按实际记录提交。


## 历史版本与验收

此前的 LabLedger 2.1 演示、发布验收记录及校验清单对应 2026 年 11 月 13 日的发布快照。GitHub 从该公开快照继续维护，完整原始开发历史由本地 Git Bundle 保管。[历史发布快照](https://github.com/yumingye/LabLedger/tree/2b3019c9de5e315b462c03704b6e55a703ddb298) · [公开历史说明](docs/PUBLIC_HISTORY_PRIVACY_AUDIT.md)
