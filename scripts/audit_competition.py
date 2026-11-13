from pathlib import Path
import json
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'final_optimization/reports'; OUT.mkdir(parents=True,exist_ok=True)
pages=['总览','数据记录','质量中心','统计分析','图表工坊','仪表盘','导出中心','实验详情','数据清洗','专业统计','实验对比','高级图表','智能分析','报告中心','系统设置']
result=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True,args=['--disable-features=DevToolsDebuggingRestrictions'])
    page=browser.new_page(viewport={'width':1440,'height':1000}); page.goto('http://127.0.0.1:8502'); page.get_by_test_id('stMetricValue').first.wait_for()
    for label in pages:
        page.get_by_test_id('stSidebar').get_by_text(label,exact=True).click(); page.wait_for_timeout(950)
        expect(page.get_by_test_id('stException')).to_have_count(0); assert '操作未完成' not in page.locator('body').inner_text()
        result.append({'page':label,'status':'PASS'})
    page.screenshot(path=str(OUT/'initial-audit.png'),full_page=True); browser.close()
(OUT/'initial-browser-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('Audited',len(result),'pages in actual Edge')
