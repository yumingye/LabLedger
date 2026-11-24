# 软件架构与设计决策

比赛版表格操作从同一 SQLite 读事务获取记录与数据集版本号。浏览器提交新增、编辑或删除时回调写入原有乐观锁事务，同时创建可恢复版本。图表预览与导出使用同一份字段选择和有效坐标规则，图表数据 CSV 仅包含当前绘制记录，双倍像素 PNG 保持用户选择的样式比例。

## 分层

Streamlit 展示层（app.py）→ 领域服务（validation / analysis / charts / exports / demo）→ Store（db.py）→ SQLite。
界面只负责收集输入与展示结果；业务函数可以独立测试。运行不依赖互联网和外部 API，首次安装依赖需要网络。

## 数据模型

- projects：id、name、created_at、updated_at（UTC ISO8601）。
- datasets：id、project_id、name、schema_json、revision。同一项目内表名唯一。
- records：id、dataset_id、payload。JSON 按字段原样保留数据；错误类型也保留供检查。
- dashboards：project_id、config。保存布局列数、图表顺序、图表配置及数据集 ID。

SQLite 开启外键，项目删除级联删除所属表、记录与仪表盘。所有数据集读写均校验 project_id。写入在事务中完成，revision 乐观锁阻止陈旧窗口覆盖新数据；时间戳随数据、名称和仪表盘修改更新。删除实验需要输入完整名称。

## 算法与边界

完整率 = 非空单元格 / 总单元格；空表显示 0%。重复数统计所有参与重复的行。数字要求有限数值；日期严格 ISO 日期。范围与 IQR 非破坏性检查，不自动填补、删除或去重。样本方差及标准差 ddof=1。趋势对有效数值对按最小二乘拟合，日期 X 转为 epoch 天数；变化率按 X 排序后首末值计算，起点零时不定义。拟合与统计不自动排除异常候选，用户需判断。

图表先转换已选 X/Y 类型，过滤不可绘制坐标；折线按 X 稳定排序。支持分组拟合。Plotly 用于交互，Matplotlib Agg 用于不依赖浏览器的 PNG 输出。柱状图不提供连续趋势线。CSV 带 UTF-8 BOM，并转义公式前缀；JSON 原始导出保存原值。

## 存储与隐私

start/install/test 脚本统一加载 scripts/env.ps1，将 TEMP、TMP、pip、Matplotlib、Python 字节码、Streamlit 配置、用户级应用目录、Playwright 浏览器全部重定向到项目根目录。USERPROFILE 的重定向也覆盖 Streamlit 可能使用的 ~/.streamlit。仅绑定 127.0.0.1。无登录与多人权限体系，定位个人本地工具，不适合直接暴露公网。

当前采用全表事务替换，适合课程实验中小型数据；20 MB 上传限制不代表性能承诺。大表、高并发与跨设备同步不在本版范围。后续可迁移增量记录更新、版本历史及批处理。

## 待参赛者审核

核心架构、统计口径、异常处理规则、交付范围与第三方资源声明须由真实参赛者确认；本文件不宣称已获审核。


## V2增量结构

project_meta(project_id,payload)关联研究设计；versions(dataset_id,revision,payload,schema_json,operation,parameters,created_at,actor)保存不可覆盖版本；history(project_id,dataset_id,kind,payload,created_at)保存操作、快照和报告索引。PRAGMA user_version=2，自动回填V1基线。旧表、ID、字段和原始记录保持兼容。保存记录使用revision乐观锁，数据替换、版本与历史在同一事务提交。恢复生成新版本。

science.py负责有限数值筛选、清洗和统计；advanced_charts.py以Plotly和Matplotlib提供交互及静态导出；reporting.py负责安全HTML、完整ZIP和JSON项目迁移；v2_ui.py只组合界面；runtime.py在应用载入绘图库前重定向可配置缓存。

输入上传不作为路径，CSV防公式注入、20MB限制、报告HTML文本转义、派生四则计算无需eval。备份使用SQLite backup API，恢复先完整性检查并备份当前库。以隔离演示库做浏览器验证；提交包采用允许列表排除data/exports/logs和缓存。
