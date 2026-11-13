from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
rows=json.loads((ROOT/'reports/licenses.json').read_text(encoding='utf-8'))
text='''# 第三方资源与许可证声明

安装依赖来自 PyPI 官方分发，下表由实际环境 pip-licenses 自动导出，涵盖运行与开发依赖。完整可获取的许可证文本保存在 reports/licenses.json。源码包不分发虚拟环境、第三方二进制或字体；安装时应遵循各包完整许可证。Streamlit 的安装元数据未附许可证文本，官方源码 LICENSE 为 Apache-2.0，见下方链接。

文档参考：[Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)、[Streamlit Dataframes](https://docs.streamlit.io/develop/concepts/design/dataframes)、[Matplotlib savefig](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.savefig.html)。界面 CSS 与应用代码本次编写，没有下载第三方界面模板、插图、Logo 或商业素材。

| 名称 | 实际版本 | 许可证（包元数据） | 官方来源 |
| --- | --- | --- | --- |
'''
for row in rows:
    text+=f"| {row['Name']} | {row['Version']} | {row['License'].replace('|','/')} | {row.get('URL','')} |\n"
text+='''
## 补充资源

- Streamlit：[官方 LICENSE](https://github.com/streamlit/streamlit/blob/develop/LICENSE)，Apache-2.0。
- Python：PSF License，[官方许可](https://docs.python.org/3/license.html)，系统 D 盘解释器，源码包不分发解释器。
- SQLite：Public Domain，[官方声明](https://sqlite.org/copyright.html)，随 Python 标准库使用。
- Windows Microsoft YaHei / SimHei：系统字体，仅在本机绘图调用，没有复制或分发字体文件。其他平台需自行配置有许可的 CJK 字体。
- Chrome / Edge：仅调用系统已安装浏览器进行验证，不随源码分发。
- Playwright 下载的 Chromium 测试浏览器：BSD 及随附第三方许可，仅存本地 .runtime；不打入交付包。
- FFmpeg：系统已安装构建，仅用于真实浏览器视频录制与 MP4 转换；FFmpeg 按构建启用项适用 LGPL/GPL，当前构建见 reports/ffmpeg-license.txt，不分发其可执行文件。
- Git / GitHub CLI：本机工具，仅用于版本管理及认证状态检查，未复制到交付包。

原始项目源码的授权由真实权利人确认，本次没有代替团队作出开源授权。正式参赛前由参赛者审核依赖清单与规则兼容性。
'''
(ROOT/'docs/THIRD_PARTY_NOTICES.md').write_text(text,encoding='utf-8')
