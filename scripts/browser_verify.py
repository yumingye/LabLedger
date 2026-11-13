"""Real-browser workflow with downloads, screenshots and optional video."""
from pathlib import Path
import json
import os
import shutil
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]

def main() -> None:
    # Use an installed browser; profile, temporary files and video all remain on D:.
    browser_path=Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    if not browser_path.exists():
        browser_path=Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    ffmpeg=shutil.which('ffmpeg')
    recorder=ROOT/'.runtime/browsers/ffmpeg-1013/ffmpeg-win64.exe'
    if ffmpeg:
        recorder.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ffmpeg,recorder)
    records=ROOT/'demo/recordings';records.mkdir(parents=True,exist_ok=True)
    result={'url':'http://127.0.0.1:8501','browser':str(browser_path),'steps':[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=str(browser_path),headless=True,args=['--disable-crash-reporter','--disable-breakpad','--no-first-run','--disable-features=DevToolsDebuggingRestrictions'])
        context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True,
                                   record_video_dir=str(records) if ffmpeg else None,
                                   record_video_size={'width':1440,'height':1000} if ffmpeg else None)
        page=context.new_page()
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        def settle():
            page.wait_for_timeout(800)
            expect(page.get_by_test_id('stException')).to_have_count(0)
            # Streamlit errors may be caught by our presentation handler.
            assert '操作未完成' not in page.locator('body').inner_text()
        def nav(label):
            page.get_by_text(label,exact=True).click();settle()
        def shot(name):
            page.wait_for_timeout(600)
            page.screenshot(path=str(ROOT/'screenshots'/name),full_page=True)
        def download(label):
            with page.expect_download() as info:page.get_by_text(label,exact=True).click()
            item=info.value
            target=ROOT/'exports'/item.suggested_filename
            item.save_as(target)
            assert target.stat().st_size>0
            result['steps'].append({'download':target.name,'bytes':target.stat().st_size})
        page.goto(result['url']);page.get_by_role('heading',name='让每一份实验数据，都有迹可循。').wait_for();settle()
        shot('01_首页.png')
        page.get_by_role('button',name='一键加载模拟实验').click();settle()
        page.get_by_text('记录总量',exact=True).wait_for();shot('02_模拟实验总览.png')
        result['steps'].append('loaded labeled simulation with 43 rows')
        nav('质量中心');shot('03_质量检查.png')
        expect(page.get_by_text('数据质量中心',exact=True)).to_be_visible()
        download('导出质量检查报告')
        nav('统计分析');shot('04_统计分析.png');download('导出趋势分析 JSON')
        nav('图表工坊')
        page.get_by_test_id('stSelectbox').filter(has_text='分组字段').click()
        page.get_by_role('option',name='实验组',exact=True).click();settle()
        for index,kind in enumerate(['折线图','柱状图','散点图']):
            control=page.get_by_test_id('stSelectbox').filter(has_text='图表类型')
            control.click();page.get_by_role('option',name=kind,exact=True).click();settle()
            expect(page.locator('.js-plotly-plot').first).to_be_visible()
            shot(f'05_{index}_{kind}.png')
            download('↓ 导出 PNG')
            result['steps'].append(f'rendered {kind}')
        page.get_by_role('button',name='＋ 添加到仪表盘').click();settle()
        nav('仪表盘');shot('06_仪表盘.png')
        page.get_by_text('3',exact=True).click();page.get_by_role('button',name='保存布局',exact=True).click();settle()
        page.reload();settle();nav('仪表盘');page.get_by_text('实验仪表盘',exact=True).wait_for()
        expect(page.get_by_role('radio',name='3',exact=True)).to_be_checked()
        result['steps'].append('dashboard layout survives browser reload')
        nav('导出中心');download('↓ 数据 CSV');download('↓ 原始数据 JSON');download('↓ 统计分析 CSV');shot('07_导出中心.png')
        nav('数据记录');shot('08_数据工作台.png')
        # Actual browser CSV upload: append a valid row to the current simulation.
        page.get_by_role('tab',name='CSV 导入').click();settle()
        csv='时间/min,温度/℃,实验组,观测日期,备注\n63,24,A · 自然冷却,2026-11-02,浏览器闭环验证\n'
        page.get_by_test_id('stFileUploader').locator('input[type=file]').set_input_files({'name':'闭环导入.csv','mimeType':'text/csv','buffer':csv.encode('utf-8-sig')})
        settle();page.get_by_role('button',name='确认导入',exact=True).click();settle()
        expect(page.get_by_test_id('stMetricValue').first).to_have_text('44')
        result['steps'].append('real CSV upload, append and persistence: 43 -> 44')
        page.reload();settle();expect(page.get_by_test_id('stMetricValue').first).to_have_text('44')
        result['steps'].append('44 rows recovered after browser reload')
        # Responsive layout check at a laptop width.
        page.set_viewport_size({'width':1280,'height':800});nav('总览');shot('09_笔记本分辨率.png')
        result['page_errors']=errors
        assert not errors
        video=page.video
        context.close()
        if video:result['video']=str(video.path().relative_to(ROOT))
        browser.close()
    (ROOT/'reports/browser-e2e.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
