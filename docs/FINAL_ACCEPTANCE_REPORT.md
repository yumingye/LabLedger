# 最终功能及仓库验收

日期：2026-11-13。本地发布准入通过；远程上传与独立 Clone 验证仍待执行，不宣布正式完成。

| 门禁 | 验收目标 | 实际命令/证据 | 状态 |
|---|---|---|---|
| G1 | 最终代码完整 | git ls-files；产品 e76020a，当前产品源码未变 | PASS |
| G2 | 原有和新增测试 | pytest -q --junitxml=reports/final-release-20261113/tests-rerun.xml；114 passed/0 failed | PASS |
| G3 | 核心功能运行 | 独立新环境 Chromium 完整9步/12下载/备份恢复/重启，0页面错误；rehearsal/result.json | PASS |
| G4 | 视频可播放且≤300秒 | ffprobe；ffmpeg -v error -i 视频 -f null -；211.32秒，exit 0 | PASS |
| G5 | 开发文档完整 | DEVELOPMENT/架构/数据模型/USER_GUIDE/AI/团队/许可 | PASS |
| G6 | README 独立部署 | 新目录联网 install.ps1、pip check、新venv114项、启动及真实浏览器均通过；rehearsal/ | PASS |
| G7 | AI/第三方/源码授权 | FINAL_AI_USAGE、THIRD_PARTY_NOTICES、SCIPY_LICENSE、licenses.json；用户明确竞赛许可 | PASS |
| G8 | 历史保全和公开隐私 | bundle verify 成功，完整原始历史本地保留；用户批准新公开快照历史，个人邮箱不入公开历史 | PASS |
| G9 | 远程文件完整 | 目标 yumingye/LabLedger；尚未推送 | PENDING |
| G10 | 评审访问 | 连接器确认 Public；公开文件访问待验证 | PENDING |
| G11 | 远程独立 Clone 部署 | 尚未推送；不得以本地快照替代 | PENDING |
| G12 | 无敏感信息 | 候选文本及全部可达历史文本blob的凭据模式扫描0命中；公开提交仅允许noreply身份 | PASS |
| G13 | SHA256 | release_inventory.py --seal逐文件生成及校验；公开快照提交前再次核对 | PASS |

阶段验收分别位于 `docs/release-stages/`。阶段 1—3 复用原冻结版本证据；阶段 4 重新完整测试；阶段 5 整理材料并验证依赖；阶段 6 等准入后上传与 Clone；阶段 7 仅全通过后交付唯一链接。

完整测试命令：加载 `scripts/env.ps1` 后，用 `.venv/Scripts/python.exe -u -m pytest -q --basetemp=.runtime/release-full-rerun -o cache_dir=.cache/release-full --junitxml=reports/final-release-20261113/tests-rerun.xml`。实际输出见 tests-rerun.txt。受限运行停滞未计为通过。没有改变测试预期或删减测试。

未解决：G9/G10/G11尚待正式推送与远程独立Clone验证，不能以已通过的本地候选验证替代。


独立本地候选：全新venv、联网锁定安装，不复用开发配置或缓存；114项通过（17.43秒）。Edge启动失败记录完整保留在rehearsal-edge-failure/，随后该副本全新下载Chromium复验通过。快速验收录像65.8秒仅用于业务检查，原脚本时长字段PARTIAL不表示门禁；正式G4使用211.32秒视频，未降低标准。
