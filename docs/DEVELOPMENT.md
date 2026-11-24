# 开发与复现

源码与 Git 仓库位于赛道一根目录。app.py 是 Streamlit 入口，labledger 中保存领域逻辑，tests 包含后端及 Streamlit AppTest，demo 包含示例数据。原有运行与存储方式沿用 Python 3.12 和 SQLite。

~~~powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
powershell -ExecutionPolicy Bypass -File .\start.ps1
powershell -ExecutionPolicy Bypass -File .\test.ps1
~~~

脚本从仓库根目录启动，将缓存、日志、数据库和依赖放入 D 盘项目内。使用 Python 3.12 在一个独立检出或解压副本安装验证。把完整的离线 wheel 目录通过 LABLEDGER_WHEELHOUSE 传给安装脚本可复现无网安装。

~~~powershell
. .\scripts\env.ps1
.\.venv\Scripts\python.exe -m playwright install --only-shell chromium
.\.venv\Scripts\python.exe scripts/verify_autosave_browser.py
~~~

浏览器脚本为每次测试创建隔离数据库、下载目录和服务日志，并启动两个相继运行的 Streamlit 进程。录制时在参数中追加 --record，FFmpeg 需在 PATH 上。真实播放文件放在 demo 目录。

早期 V2.1 架构及原发布复验方式见 [历史架构](FINAL_ARCHITECTURE.md) 和 [历史发布快照](https://github.com/yumingye/LabLedger/tree/2b3019c9de5e315b462c03704b6e55a703ddb298)。公开分支沿发布快照维护，原始开发历史保存在本地 Git Bundle。
