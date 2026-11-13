# 最终架构与数据流

Streamlit展示(app.py/v2_ui.py/dossier_ui.py) → Store参数化SQLite与revision乐观锁 → validation/science本地质量、清洗、统计 → archive可执行档案/诊断/方案对照 → Plotly与Matplotlib → reporting安全HTML及完整ZIP。

数据表：projects、datasets、records、dashboards沿用V1；project_meta保存结构化研究设计和实验方案；versions保存原始/处理数据、字段定义、参数、时间与操作者；history保存分析、图表、报告索引、诊断和自包含数字档案。索引覆盖版本dataset/revision及项目history。兼容迁移由Store和scripts/migrate_v2.py执行，先备份原库。仪表盘工作空间计数用SQL聚合，避免把所有数据读入Pandas。

数字档案：包含字段、原始/清洗版本、逐步操作、统计方法与结果、图表配置、软件版本和SHA256。重跑按保存手工版本载入，对清洗步骤重新执行并核对中间结果，再重算描述、相关、回归和置信区间。结果按1e-9容差比较。哈希不是身份签名，不能证明测量真实性；旧软件环境差异可能导致可见差异，不隐瞒。

安全：上传20MB，项目结构预检并失败清理；受控文件名与根目录；CSV公式前缀转义；HTML文本/表格转义；无eval；无远程模型默认调用；删除与恢复确认；报告以版本/结论判断过期、每次唯一归档。数据库恢复先完整性检查和当前库备份。不是多用户权限系统，不承诺敌对SQLite文件在高权限桌面环境的完整隔离。

运行目录动态取源码根，脚本把TEMP、缓存、Matplotlib、用户配置及浏览器临时文件指向项目D盘。最终独立部署在全新目录、新venv，使用原始缓存wheel安装，不复制开发site-packages。系统Edge、Windows字体和FFmpeg仅作本机工具，不分发二进制。
