"""Actual Edge E2E and paced 3 minute recording; pauses allow reading results."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import time
from urllib.request import build_opener,ProxyHandler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright,expect
from labledger.db import Store
from labledger.demo_v2 import load_algorithm_demo

ROOT=Path(__file__).resolve().parents[1]
SPEED=float(os.environ.get('DEMO_SPEED','1'))
DB=ROOT/'data/v2_browser.sqlite3'
URL='http://127.0.0.1:8502'

def main():
    store=Store(DB)
    if not store.projects(): load_algorithm_demo(store)
    dest=ROOT/'demo/recordings'; dest.mkdir(exist_ok=True)
    ffmpeg=shutil.which('ffmpeg'); assert ffmpeg,'FFmpeg is required for real recording'
    recorder=ROOT/'.runtime/browsers/ffmpeg-1013/ffmpeg-win64.exe'; recorder.parent.mkdir(parents=True,exist_ok=True)
    if not recorder.exists(): shutil.copy2(ffmpeg,recorder)
    result={'steps':[],'downloads':[],'url':URL}; errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True,args=['--disable-crash-reporter','--disable-breakpad','--no-first-run','--disable-features=DevToolsDebuggingRestrictions'])
        context=browser.new_context(viewport={'width':1600,'height':1000},accept_downloads=True,record_video_dir=str(dest/'v2_raw'),record_video_size={'width':1600,'height':1000})
        page=context.new_page(); page.on('pageerror',lambda e:errors.append(str(e)))
        start=time.monotonic()
        def check():
            page.wait_for_timeout(650)
            expect(page.get_by_test_id('stException')).to_have_count(0)
            assert '操作未完成' not in page.locator('body').inner_text()
        def note(text,seconds=3):
            # Commentary overlay labels actual visible operations, not simulated application results.
            page.evaluate("text=>{let el=document.getElementById('demo-caption');if(!el){el=document.createElement('div');el.id='demo-caption';document.body.appendChild(el)};el.textContent=text;Object.assign(el.style,{position:'fixed',bottom:'12px',left:'350px',right:'30px',zIndex:999999,background:'#102c4a',color:'white',padding:'14px 24px',borderRadius:'12px',font:'18px Microsoft YaHei',boxShadow:'0 4px 20px #0003'})}",text)
            page.wait_for_timeout(seconds*1000*SPEED)
        def nav(label):
            page.get_by_test_id('stSidebar').get_by_text(label,exact=True).click(); check()
        def choose(label,value):
            field=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label,exact=True)).get_by_role('combobox')
            if field.input_value()==value: return
            field.fill(value); page.wait_for_timeout(150); field.press('ArrowDown'); field.press('Enter'); check()
            expect(field).to_have_value(value)
        def click(label): page.get_by_role('button',name=label,exact=True).click(); check()
        def download(label):
            with page.expect_download() as event: page.get_by_text(label,exact=True).click()
            download=event.value; target=ROOT/'exports/v2/browser'/download.suggested_filename; target.parent.mkdir(parents=True,exist_ok=True); download.save_as(target)
            assert target.stat().st_size>0; result['downloads'].append({'name':target.name,'bytes':target.stat().st_size})
        def shot(name): page.screenshot(path=str(ROOT/'screenshots'/f'v2_{name}.png'),full_page=True)
        page.goto(URL); page.get_by_role('heading',name='让每一份实验数据，都有迹可循。').wait_for(); check()
        note('LabLedger V2｜面向大学生实验课程与科研入门的本地数据管理、分析和报告工具',6)
        note('闭环：创建实验 → 导入与检查 → 可追溯清洗 → 统计对比 → 图表与报告',5); shot('01_dashboard')
        page.get_by_text('＋ 创建实验',exact=True).click()
        page.get_by_role('textbox',name='实验名称',exact=True).fill('竞赛演示 · 算法性能合成实验')
        click('创建实验'); note('为每个实验独立管理数据与研究条件，切换实验不会混入其他实验记录',4)
        page.get_by_text('实验设置 / 新建数据表',exact=True).click(); click('创建算法性能模板数据表')
        nav('数据记录'); page.get_by_role('tab',name='CSV 导入').click(); check()
        page.locator('input[type=file]').set_input_files(str(ROOT/'demo/templates/算法性能示例.csv')); check()
        note('真实CSV上传｜字段识别与预览：三种算法、四种输入规模、每条件十次重复；数据为合成演示',5)
        click('确认导入'); expect(page.get_by_test_id('stMetricValue').first).to_have_text('121'); result['steps'].append('created experiment, schema, CSV upload 121 rows'); shot('02_import')
        nav('实验详情'); page.get_by_role('textbox',name='实验目标',exact=True).fill('比较相同输入规模下算法的耗时与稳定性')
        page.get_by_role('textbox',name='数据来源',exact=True).fill('本数据为软件功能展示用合成数据，不代表真实实验测量结果。')
        click('保存实验详情'); note('记录实验目标、方法、自变量、环境与数据来源，让分析具有上下文',4)
        nav('数据清洗'); note('公开质量评分公式：按问题单元格与重复行扣分；异常只是候选提示',5); shot('03_quality')
        choose('处理操作','删除重复行'); click('预览处理结果'); note('处理前后并排预览：121行 → 120行，点击保存前不会改动原数据',5)
        click('保存为新版本'); expect(page.get_by_test_id('stMetricValue').first).to_have_text('120')
        choose('处理操作','中位数填充'); choose('处理字段','运行时间'); click('预览处理结果'); note('中位数填补缺失耗时；每次清洗生成新版本，保存操作、参数、时间和操作者',4); click('保存为新版本')
        choose('处理操作','异常值标记'); choose('处理字段','运行时间'); click('预览处理结果'); note('IQR默认标记异常而不删除；原始121行数据仍保存在版本链中',5); click('保存为新版本'); result['steps'].append('deduplicate, median fill, IQR mark, retained original version'); shot('04_versions')
        nav('专业统计'); note('专业描述统计：样本量、四分位数、方差、变异系数、偏度和峰度均由数据计算',5)
        choose('因变量','运行时间'); note('相关性矩阵与回归方程、R²、残差诊断：明确相关不代表因果',5)
        page.get_by_text('回归自变量',exact=True).first.scroll_into_view_if_needed(); note('模型适用性检查会拦截样本不足与完全共线；假设检验条件不满足时不强行推断',5)
        click('保存分析快照'); result['steps'].append('statistics regression snapshot'); shot('05_statistics')
        nav('实验对比'); note('按算法或实验项目比较均值、标准差与相对变化；可选择多个实验的数据集',5)
        choose('分层控制字段','输入规模'); control=page.get_by_test_id('stMultiSelect').filter(has=page.get_by_text('保留条件',exact=True)).locator('input'); control.fill('100'); control.press('ArrowDown'); control.press('Enter'); page.keyboard.press('Escape'); check()
        note('固定输入规模100，控制混杂条件，再看组间分布与稳定性；不凭一次测量宣称普遍优势',6)
        click('保存对比结果'); result['steps'].append('stratified algorithm comparison saved'); shot('06_comparison')
        nav('高级图表'); choose('高级X轴','输入规模'); choose('高级Y轴','运行时间'); choose('高级分组','算法名称')
        page.get_by_role('textbox',name='高级图表标题',exact=True).fill('算法耗时与输入规模（合成数据）'); page.keyboard.press('Tab'); check()
        note('科研风格图表：自定义标题、单位、分组、颜色、尺寸和筛选条件',5); download('下载高级图表 PNG'); click('保存图表分析记录'); shot('07_line')
        choose('高级图表类型','箱线图'); choose('高级X轴','算法名称'); note('箱线图展示分布及极端值，平均值之外也要关注波动与异常',5); download('下载高级图表 SVG'); shot('08_box')
        choose('高级图表类型','热力图'); note('热力图展示数值指标的相关结构；支持PNG、SVG与离线交互HTML',5); download('下载交互图表 HTML'); shot('09_heatmap'); result['steps'].append('line box heatmap, PNG SVG HTML downloads')
        nav('智能分析'); note('本地统计规则引擎，非大模型：每条建议显示样本量、均值、标准差及相关系数依据',6)
        page.get_by_role('textbox',name='可编辑实验结论',exact=True).scroll_into_view_if_needed(); note('结构化结论草稿可编辑，包含发现、关键数据、局限性和后续建议',5); click('保存结论草稿'); shot('10_insights')
        nav('报告中心'); note('一键汇总研究目的、数据质量、清洗版本、统计、回归、对比和结论',5); click('生成完整实验报告')
        download('下载报告 HTML'); download('下载报告 MD'); download('下载报告 ZIP'); download('下载报告 CSV附件'); download('下载报告 PNG')
        page.get_by_text('报告正文预览',exact=True).scroll_into_view_if_needed(); note('完整报告包内含HTML、Markdown、CSV、PNG与可复现项目JSON；报告图表由当前数据生成',6)
        page.mouse.wheel(0,650); note('报告保留分析依据、清洗过程与局限，结论仍需使用者复核',5); shot('11_report'); result['steps'].append('report generated and five export formats downloaded')
        nav('系统设置'); click('创建数据库备份'); download('下载数据库备份'); download('导出完整实验项目 JSON'); note('操作历史、数据版本、分析参数和报告记录均保存在SQLite；可备份或导入隔离副本',5)
        # Restart a separate real service against the exact same saved database.
        env=os.environ.copy(); env['LABLEDGER_DB']=str(DB)
        log=(ROOT/'logs/v2_restart.log').open('w',encoding='utf-8')
        process=subprocess.Popen([sys.executable,'-m','streamlit','run','app.py','--server.port','8503'],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        opener=build_opener(ProxyHandler({}))
        try:
            for _ in range(80):
                try:
                    if opener.open('http://127.0.0.1:8503/_stcore/health',timeout=1).status==200: break
                except OSError: time.sleep(.25)
            else: raise RuntimeError('restart health timeout')
            process.terminate(); process.wait(timeout=20)
            process=subprocess.Popen([sys.executable,'-m','streamlit','run','app.py','--server.port','8503'],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(2)
            page.goto('http://127.0.0.1:8503'); expect(page.get_by_test_id('stMetricValue').first).to_have_text('120',timeout=30000); check()
            nav('系统设置'); note('真实服务进程重启后重新打开实验：120条记录、清洗版本与分析报告历史仍然存在',6); shot('12_restart')
            nav('数据清洗'); page.get_by_text('版本历史与恢复',exact=True).scroll_into_view_if_needed(); note('从原始数据到每一步处理，都有迹可循。LabLedger让个人实验更可复核、可表达、可复现。',5)
            result['restart']='PASS'; result['steps'].append('real process stop/start, 120 rows and history restored')
        finally: process.terminate(); process.wait(timeout=20); log.close()
        result['page_errors']=errors; assert not errors
        result['elapsed_seconds']=round(time.monotonic()-start,2); video=page.video; context.close(); raw=video.path(); browser.close()
    output=dest/('LabLedger_3min_真实浏览器演示_v2.mp4' if SPEED==1 else 'v2_preflight.mp4')
    subprocess.run([ffmpeg,'-y','-i',str(raw),'-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p',str(output)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    probe=Path(ffmpeg).with_name('ffprobe.exe')
    duration=float(subprocess.check_output([str(probe),'-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(output)]))
    result.update(video=str(output),duration=duration,status='PASS' if 180<=duration<=220 else 'PARTIAL')
    (ROOT/'reports/browser-v2.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
