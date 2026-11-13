# 最终功能及仓库验收

日期：2026-11-13（Asia/Shanghai）。七阶段完成，G1—G13全部 PASS。唯一正式交付：[GitHub 仓库](https://github.com/yumingye/LabLedger)。

| 门禁 | 验收目标 | 实际测试及命令 | 证据位置 | 状态 |
|---|---|---|---|---|
| G1 | 最终代码完整 | git diff e76020a -- app.py labledger tests；严格发布清单及Clone逐项比对 | product-unchanged.txt、product-reproduction.json | PASS |
| G2 | 原有及新增测试 | 新Clone .venv/python -m pytest -q --junitxml=reports/fresh-verification/tests.xml；114 passed/0 failed，31.46秒 | remote/tests.txt、remote/tests.xml | PASS |
| G3 | 核心业务真实运行 | 新Clone .venv/python scripts/verify_final_release.py；9步、12下载、备份恢复、重启、0页面错误 | remote/result.json、remote/browser-full-flow.txt | PASS |
| G4 | 正式视频可播放且不超过300秒 | ffprobe -v error -show_entries format=duration,size；ffmpeg -v error -i 正式MP4 -f null -；211.32秒、H.264、1600×1000、解码exit0 | video-probe.json、video-status.txt、remote-video-status.txt | PASS |
| G5 | 开发和评审文档完整 | 必需材料存在性断言，README所有仓库相对链接检查0失效 | product-reproduction.json、inventory-check.json | PASS |
| G6 | README可独立部署 | 真实远程Clone、新venv、powershell -File install.ps1、pip check、健康HTTP200、真实浏览器 | remote/remote-fresh-install-retry.txt、remote/pip-check.txt、remote/result.json | PASS |
| G7 | AI、第三方许可及源码授权 | 检查AI披露、包许可原文、SciPy附属许可及用户明确竞赛限定授权，无分发第三方可执行文件 | docs/FINAL_AI_USAGE.md、docs/THIRD_PARTY_NOTICES.md、LICENSE_NOTICE.md | PASS |
| G8 | 完整历史保全及公开隐私 | git bundle verify；原6项目提交本地完整保留；按用户批准公开历史从noreply快照开始 | bundle-verification.txt、docs/PUBLIC_HISTORY_PRIVACY_AUDIT.md | PASS |
| G9 | 远程文件完整 | git clone唯一公开URL；首个发布235文件、234项哈希通过；后续仅补验收元数据并重新校验 | remote-clone.txt、remote/clone-hash-verification.txt | PASS |
| G10 | 评审未登录访问 | 无Cookie/Authorization的HTTP：公开仓库、README渲染、源码文档和视频200，远程视频SHA一致 | public-access.json、verify_public_access.py | PASS |
| G11 | 远程独立Clone部署及核心验证 | 从GitHub新Clone，不复用开发依赖/缓存/配置；重新联网安装包和Chromium，完整测试/实际业务/重启通过 | remote/result.json、product-reproduction.json、remote/remote-browser-install.txt | PASS |
| G12 | 敏感信息和缓存排除 | release_inventory.py扫描候选及全部原始历史文本blob：0模式命中；独立公开提交只用noreply；暂存集合等于清单 | inventory-check.json、docs/PUBLIC_HISTORY_PRIVACY_AUDIT.md | PASS |
| G13 | SHA256逐文件校验 | release_inventory.py --seal；逐文件SHA256，清单自身排除；Clone重新验证，不以ZIP代替 | docs/FINAL_RELEASE_SHA256.txt、remote/clone-hash-verification.txt | PASS |

证据未特别注明的路径均相对于 `reports/final-release-20261113/`；docs/、LICENSE_NOTICE.md 从仓库根定位。源码运行及测试对应远程提交 `6c90f0be5adfcd0a01e6ad2216b5493d4421e3c7`。最终补充提交仅更新验收材料、清单、哈希和忽略规则；产品、依赖锁、环境/验证脚本与该受测SHA逐字节一致，最终main以Git提交记录为准。

本轮通过数量为114项独立测试（原39+新增75），不是把多次运行相加。原环境17.56秒，本地新候选17.43秒，远程Clone31.46秒。真实浏览器9步/12下载包括CSV上传、3次版本清洗、统计、分层对比、图表导出、档案封存重跑、条件诊断/方案对照、报告、数据库备份上传恢复及真实进程停止重启。

发现及修复：正式视频Git忽略、README旧状态及部署说明、使用教程恢复说明、源码授权缺失、历史邮箱公开风险、PowerShell自动缓存进入暂存的风险、Edge在隔离环境启动失败。保持产品功能冻结，测试断言未改。详见FINAL_RELEASE_AUDIT.md。

完整失败记录保留：首次受限测试停滞未计PASS；候选Edge启动失败后用本目录新下载Chromium实际重验；远程首次PyPI TLS EOF失败后正常重试成功，未关闭证书校验或复制开发包。快速业务录像的旧脚本PARTIAL只指时长，不是门禁；G4使用独立211.32秒正式视频。

目录：app.py+labledger/源码，tests/测试，scripts/运行验证，requirements*.txt依赖，docs/开发/架构/数据库/AI/团队/许可/验收，demo/合成数据和正式MP4，reports/及final_optimization/reports/历史和本轮证据。详见FINAL_REPOSITORY_MANIFEST.md。

尚未解决的工程发布阻塞：无。达到本任务定义的仓库发布及技术参赛提交条件，可使用唯一仓库链接提交。赛事报名、身份资格及官方AI/原创性审核由赛事与参赛者完成，本工程验收不冒称官方审核通过。已知产品限制保留：Windows单机、单用户、无真实用户研究/压力或跨OS矩阵、多重比较未校正、PDF/Ollama未集成；这些不在既定门禁范围，不虚报为已验证功能。

原始开发历史和原始交付全部保存在D盘；公开历史按用户明确批准从干净快照开始，不含原始个人邮箱。仅一个GitHub正式仓库，没有强推或改写原始历史。
