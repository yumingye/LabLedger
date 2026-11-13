from pathlib import Path
import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
browser=json.loads((ROOT/'reports/browser-v2.json').read_text(encoding='utf-8'))
cases=ET.parse(ROOT/'reports/junit-v2.xml').findall('.//testcase')
assert len(cases)==86 and not any(c.find('failure') is not None or c.find('error') is not None for c in cases)
assert browser['restart']=='PASS' and not browser['page_errors'] and 180<=browser['duration']<=220
old={}
for path in [ROOT/'交付成果/LabLedger_Final_Submission.zip',ROOT/'demo/recordings/LabLedger_真实浏览器演示.mp4',ROOT/'交付成果/SHA256SUMS.txt']:
    old[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
original_zip=ROOT/'交付成果/LabLedger_Final_Submission.zip'
checksum=ROOT/'交付成果/LabLedger_Final_Submission.zip.sha256'
assert checksum.read_text().split()[0]==old[original_zip.name]
safety={'original_artifacts_preserved':old,'original_zip_checksum':'PASS','sql':'parameterized values; fixed table identifiers','csv_formula_guard':'original tests preserved','file_limits':'20MB CSV/project/database upload','report_html':'html.escape for user text','derived_fields':'explicit arithmetic, no eval','runtime':{key:os.environ.get(key) for key in ['TEMP','TMP','MPLCONFIGDIR','PIP_CACHE_DIR','PLAYWRIGHT_BROWSERS_PATH','PYTHONPYCACHEPREFIX']},'limits':'No OS-wide disk audit; OS event logs and installed tool binaries are outside app control. No remote model calls. No user database packaged.'}
(ROOT/'reports/v2-safety.json').write_text(json.dumps(safety,ensure_ascii=False,indent=2),encoding='utf-8')
rows=[('G1','原39项测试','PASS','29核心+10原UI，原测试文件无修改'),('G2','新增测试','PASS','38计算与导出+9页面交互'),('G3','多实验管理','PASS','CRUD、元信息、跨实验隔离及重开'),('G4','清洗与版本恢复','PASS','15种处理参数化测试、异常过滤确认与恢复模式'),('G5','统计正确性','PASS','已知均值/方差/相关/回归与检验边界'),('G6','实验对比','PASS','真实浏览器分层算法对比，单测跨项目导入隔离'),('G7','高级图表','PASS','12种图表单测，PNG/SVG/HTML真实下载'),('G8','智能分析证据','PASS','本地计算依据及非大模型声明'),('G9','报告','PASS','完整ZIP成员与HTML转义，浏览器5种附件下载'),('G10','备份恢复','PASS','SQLite备份后重新打开恢复全部历史；项目JSON往返'),('G11','真实浏览器闭环','PASS','创建、CSV、三次清洗、统计、对比、图表、报告'),('G12','服务重启恢复','PASS','真实服务进程停止重启，120行和版本历史恢复'),('G13','D盘存储','PASS','可配置目录均指向D盘；不等于OS全盘写入审计'),('G14','文档','PASS','README及V2指定文档齐全'),('G15','单人信息','PASS','无虚构成员，人工审核状态如实披露'),('G16','三分钟视频','PASS',f'实测{browser["duration"]:.2f}秒，真实Edge录制'),('G17','ZIP及SHA256','PASS','build_v2_submission强制CRC和逐项SHA256，详见外部校验JSON')]
text='# V2 测试与验收报告\n\n2026-11-12。实际全套86项通过，原39项保留且未修改断言，新增47项通过。证据：reports/junit-v2.xml、pytest-v2.txt、browser-v2.json、v2-safety.json。\n\n| 门禁 | 项目 | 状态 | 证据与范围 |\n|---|---|---|---|\n'+'\n'.join('| '+' | '.join(row)+' |' for row in rows)+'\n\n浏览器完整下载列表及字节数见browser-v2.json。原有两次沙箱测试停滞，允许本地环回通信后完整测试通过；未把停滞运行记为通过。没有进行大数据压力或多浏览器矩阵。PDF/Ollama是可选项未实现；图表快照未自动填回编辑器，详见升级报告。\n\n旧版历史报告只描述V1，不作为V2验收证据。版权与参赛资格需本人最终确认，本报告不保证获奖。\n'
(ROOT/'docs/TEST_REPORT_V2.md').write_text(text,encoding='utf-8')
state={'phase':'V2 frozen before competition optimization','tests':86,'original_tests':39,'new_tests':47,'browser':browser,'next':'Audit V2 release first; then serial three-round competition optimization. Preserve V1 and V2 release artifacts.','known_limits':['No Ollama/PDF','chart snapshot editor restoration partial','single user local tool','human competition eligibility/license approval pending']}
(ROOT/'reports/V2_STAGE_STATE.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
print('V2 stage reports ready')
