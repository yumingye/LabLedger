# 开发与验证

运行环境为 Windows、Python 3.12。从仓库根运行 `install.ps1`，安装锁定的运行和测试依赖。源码结构与数据库详见 [最终架构](FINAL_ARCHITECTURE.md) 及 [数据设计](ARCHITECTURE.md)。Store 首次连接自动建表及迁移，无外部数据库服务、密钥或模型文件。

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
powershell -ExecutionPolicy Bypass -File .\test.ps1
```

测试覆盖 CRUD、事务持久化、乐观锁、CSV、隔离、类型异常、统计参考值、图表输出、清洗链重跑、档案篡改、项目往返和 Streamlit 页面交互。JUnit 和实际日志以 [最终验收](FINAL_ACCEPTANCE_REPORT.md) 索引为准。

`scripts/env.ps1` 使脚本在自身项目根目录工作，将受控临时目录、pip、绘图和配置缓存定位在项目内。不要删除或提交个人数据库。新增字段或清洗步骤应保留原始版本；统计实现应使用已知参考数据验证，不能调整原测试预期掩盖缺陷。

浏览器验收额外需要浏览器和 FFmpeg；它们不属于产品启动依赖。最终验证脚本使用在该副本内全新下载的 Playwright Chromium，具体命令见 README。历史 `browser_competition.py` 为三轮和正式视频录制脚本，默认会输出正式视频，复跑需在独立目录或设置唯一 ITERATION 和 DEMO_SPEED，避免覆盖历史成果。支持 LABLEDGER_BROWSER_EXECUTABLE 环境变量，空值表示 Playwright 浏览器。最终发布验证脚本使用独立目录及独立端口，所有新产物写 D 盘。

原始开发历史完整保留在参赛者本地。依明确隐私授权，公开 Git 历史从发布快照开始，原始历史不随公开仓库分发，详见 [隐私审计](PUBLIC_HISTORY_PRIVACY_AUDIT.md)。旧版测试和交付报告仅描述对应历史版本。
