"""Verify a fresh LabLedger project, autosave, real downloads and restart."""

import argparse
import csv
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

from PIL import Image
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "课堂测量 · 浏览器验收"


@contextmanager
def server(port, run):
    url = f"http://127.0.0.1:{port}"
    env = {**os.environ, "LABLEDGER_DB": str(run / "lab.sqlite3")}
    opener = build_opener(ProxyHandler({}))
    with (run / "server.txt").open("ab") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app.py", "--server.address",
             "127.0.0.1", "--server.port", str(port), "--server.headless", "true"],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(100):
                if process.poll() is not None:
                    break
                try:
                    with opener.open(url + "/_stcore/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(.2)
            else:
                raise RuntimeError("Streamlit health check timed out")
            if process.poll() is not None:
                raise RuntimeError("Streamlit exited before verification")
            yield url
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)


def hold(page, text, record, seconds=10):
    if not record:
        return
    page.evaluate(
        """text => {
          document.querySelector('#demo-subtitle')?.remove();
          const caption = document.createElement('aside');
          caption.id = 'demo-subtitle';
          caption.textContent = text;
          caption.style.cssText = 'position:fixed;bottom:30px;left:50%;transform:translateX(-50%);'
            + 'background:#102b35;color:white;padding:14px 25px;border-radius:8px;'
            + 'font:24px Microsoft YaHei,sans-serif;box-shadow:0 4px 16px #0006;z-index:99999';
          document.body.appendChild(caption);
        }""",
        text,
    )
    page.wait_for_timeout(seconds * 1000)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="browser-labledger-", dir=runtime))
    print(f"Evidence directory: {run}", flush=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get("LABLEDGER_BROWSER_EXECUTABLE") or None,
            args=["--disable-crash-reporter", "--disable-breakpad", "--no-first-run"],
        )
        viewport = {"width": 1920, "height": 1080}
        context = browser.new_context(
            viewport=viewport, record_video_dir=run if args.record else None,
            record_video_size=viewport if args.record else None,
        )
        page = context.new_page()
        sidebar = page.get_by_test_id("stSidebar")
        metrics = page.get_by_test_id("stMetricValue")

        def nav(label):
            sidebar.get_by_text(label, exact=True).click()

        def download(label):
            with page.expect_download() as event:
                page.get_by_role("button", name=label).click()
            path = run / event.value.suggested_filename
            event.value.save_as(path)
            return path

        with server(port, run) as url:
            page.goto(url)
            expect(page.get_by_role("heading", name="让每一份实验数据，都有迹可循。")).to_be_visible()
            hold(page, "数迹实验数据工坊 LabLedger · 从记录到图表和复验", args.record)
            page.get_by_role("textbox", name="实验名称").fill(PROJECT)
            page.get_by_role("button", name="创建实验", exact=True).click()
            page.get_by_text("实验设置 / 新建数据表", exact=True).click()
            page.get_by_role("button", name="创建数据表", exact=True).click()
            expect(metrics.first).to_have_text("0")
            hold(page, "创建独立实验与数据表，字段包括时间、测量值和分组", args.record)
            nav("数据记录")
            page.get_by_role("tab", name="CSV 导入").click()
            page.locator("input[type=file]").set_input_files(ROOT / "demo" / "competition_sample.csv")
            expect(page.get_by_role("button", name="确认导入")).to_be_enabled()
            hold(page, "导入四条用于验证流程的示例数据，先预览再确认", args.record)
            page.get_by_role("button", name="确认导入").click()
            expect(metrics.first).to_have_text("4")
            nav("质量中心")
            expect(page.get_by_text("发现待检查项", exact=False)).to_be_visible()
            hold(page, "质量中心标出无法参与数值绘图的示例输入", args.record)
            nav("数据记录")
            page.get_by_role("tab", name="录入与编辑").click()
            page.get_by_text("逐字段编辑（自动保存）", exact=True).click()
            field = page.get_by_role("textbox", name="时间 · 自动保存", exact=True)
            expect(field).to_have_value("1")
            field.fill("1.5")
            field.press("Enter")
            expect(page.get_by_text("表格修改已自动保存。", exact=True)).to_be_visible()
            with sqlite3.connect(run / "lab.sqlite3") as db:
                payload = db.execute("SELECT payload FROM records ORDER BY id LIMIT 1").fetchone()[0]
                assert json.loads(payload)["时间"] == "1.5", payload
            hold(page, "在录入页逐字段编辑，提交后自动写入 SQLite 并生成版本", args.record)
            nav("图表工坊")
            title = page.get_by_role("textbox", name="图表标题", exact=True)
            title.fill("测量值随时间变化")
            title.press("Tab")
            page.get_by_text("更多样式", exact=True).click()
            slider = page.get_by_test_id("stSlider").filter(has_text="字体字号").get_by_role("slider")
            slider.press("ArrowRight")
            expect(slider).to_have_value("15")
            grid = page.get_by_role("checkbox", name="显示网格")
            grid.press("Space")
            expect(grid).not_to_be_checked()
            expect(page.get_by_text("共绘制 3 条有效记录", exact=False)).to_be_visible()
            hold(page, "改标题、字号与网格；图表使用三个有效观测", args.record)
            exported_image = download("导出 PNG")
            exported_csv = download("图表数据 CSV")
            with Image.open(exported_image) as png:
                assert png.size == (2000, 960), png.size
                png.verify()
            with exported_csv.open(encoding="utf-8-sig", newline="") as handle:
                points = list(csv.DictReader(handle))
            assert len(points) == 3 and points[0]["时间"] == "1.5", points
            hold(page, "真实下载：高清 PNG 为 2000×960，CSV 包含同一张图的有效观测", args.record)
            page.screenshot(path=run / "chart.png")
        with server(port, run):
            page.reload()
            expect(metrics.first).to_have_text("4")
            nav("数据记录")
            page.get_by_role("tab", name="录入与编辑").click()
            page.get_by_text("逐字段编辑（自动保存）", exact=True).click()
            expect(page.get_by_role("textbox", name="时间 · 自动保存", exact=True)).to_have_value("1.5")
            hold(page, "关闭并重启应用后，原实验、四条记录和刚才的表格修改均已恢复", args.record, 15)
        video = page.video
        context.close()
        browser.close()
        if video:
            destination = ROOT / "demo" / "LabLedger_自动保存与导出.mp4"
            subprocess.run(
                ["ffmpeg", "-n", "-i", str(video.path()), "-c:v", "libx264",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(destination)],
                cwd=ROOT, check=True,
            )
    print("PASS: isolated project → CSV → quality → autosave → chart PNG and CSV → restart")


if __name__ == "__main__":
    main()
