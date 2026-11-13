# 最终测试与验收报告

> 历史冻结报告（2026-11-12）：下文旧门禁编号与 PARTIAL 状态原样保留用于追溯。本次 2026-11-13 仓库发布仅以 [FINAL_ACCEPTANCE_REPORT.md](FINAL_ACCEPTANCE_REPORT.md) 的 G1—G13 为准。

2026-11-12。总计114项测试，原39项保留，新增75项；当前通过状态：True。原测试没有删除、降断言或改预期。完整JUnit、文本输出及浏览器下载记录位于final_optimization/reports。

| 门禁 | 项目 | 状态 | 验证范围 |
|---|---|---|---|
| G1 | 原39项测试 | PASS | 原test_core.py/test_ui.py未修改 |
| G2 | 新增测试 | PASS | 75新增；总计114 |
| G3 | 核心业务闭环 | PASS | 三轮真实Edge创建、CSV、清洗、统计、对比、图表、报告 |
| G4 | 统计独立核验 | PASS | 人工可验方差/回归，独立Student-t积分p值及已知t区间 |
| G5 | 实验可复现 | PASS | 清洗链中间版本核对、模型重算、哈希与差异、导入后重跑 |
| G6 | 安全异常输入 | PASS | 20MB、畸形CSV/JSON、公式、路径、SQL、删除后档案 |
| G7 | 真实UI浏览器 | PASS | 全部初始页面审查，三轮完整闭环及新增控件 |
| G8 | 独立目录部署 | PASS | 从ZIP解压、新venv离线安装、全部测试、真实UI及重启；同一Windows机 |
| G9 | 文档 | PASS | README、阶段/架构/AI/最终测试报告 |
| G10 | AI与版权 | PARTIAL | 第三方许可证与AI披露已整理；源码授权、赛事规则需本人核实 |
| G11 | 单人信息 | PASS | 无虚构成员和人工贡献 |
| G12 | 最终视频 | PASS | 实测211.32秒；字幕版、无配音 |
| G13 | ZIP逐文件哈希 | PASS | build_competition.py强制检查CRC、字节数和SHA256；外部校验JSON |
| G14 | Git与Bundle | PASS | 最终本地提交与Bundle校验后以外部证据为准 |
| G15 | D盘存储 | PASS | 受控数据、缓存、测试、安装、录制与导出均D盘；非OS全盘审计 |

测试覆盖：CSV异常、空/单行/常数/单数值列、非法类型、20MB上限、公式注入、路径净化、SQL参数、坏JSON无半成品、数据隔离、重复导入副本、删除后独立档案、过期报告拦截、归档唯一性、t区间、独立积分p值、数字档案篡改和差异检测、所有图表导出。浏览器第三轮还实际上传数据库备份并恢复；详情见browser-round3.json。

性能：{"rows": 10000, "seed": 77, "seconds": {"describe": 0.003904199998942204, "conditional_cleaning": 0.0036687999963760376, "save_with_version": 0.03612589999102056, "sql_counts": 0.0022705000010319054}, "counts": {"projects": 1, "datasets": 1, "records": 10000}, "scope": "one warm local run, not a throughput guarantee or stress test"}

范围限制：单机Windows，非第二台机器/OS；性能仅单次一万行测量，不是压力上限；没有多浏览器全矩阵、真实科研测量或用户研究。G10/G14人工/最终归档条件不得误读为官方审核通过。V1/V2历史报告只适用于其冻结版本。
