#!/usr/bin/env python3
"""
盐选故事投稿 — Playwright自动化提交
用法: python salt_submit.py <story_directory>
"""
import sys, os, json, time
from pathlib import Path
from datetime import datetime

def load_cookies():
    cookie_file = Path.home() / ".mpub" / "cookies" / "zhihu.json"
    if cookie_file.exists():
        return json.loads(cookie_file.read_text(encoding="utf-8"))
    return None

def submit_story(story_dir):
    """Submit盐选故事 via知乎创作中心"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SETUP] pip install playwright && playwright install chromium")
        return False

    story_path = Path(story_dir)
    if not story_path.exists():
        print(f"[FAIL] 目录不存在: {story_dir}")
        return False

    # Collect all chapter files
    chapters = sorted(story_path.glob("*.md"))
    if not chapters:
        print(f"[FAIL] 无.md文件: {story_dir}")
        return False

    print(f"[STORY] {len(chapters)}章待提交:")
    for c in chapters:
        print(f"  - {c.name}")

    cookies = load_cookies()
    if not cookies:
        print("[FAIL] 未找到知乎Cookie。先运行: mpub login -p zhihu")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Headful for debugging
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()

        # Navigate to creator center → 盐选创作
        print("[NAV] 进入知乎创作中心...")
        page.goto("https://www.zhihu.com/creator/creation", timeout=30000)
        page.wait_for_timeout(3000)

        # Look for盐选/盐言故事 submission entry
        try:
            # Try to find the盐选 submission button
            salt_btn = page.query_selector("text=盐选") or page.query_selector("text=盐言") or page.query_selector("text=投稿")
            if salt_btn:
                salt_btn.click()
                page.wait_for_timeout(2000)
                print("[OK] 进入盐选投稿页面")
            else:
                # Try direct URL
                page.goto("https://www.zhihu.com/creator/creation/salt", timeout=30000)
                page.wait_for_timeout(2000)
                print("[NAV] 尝试盐选直接链接...")
        except Exception as e:
            print(f"[WARN] 盐选入口未找到: {e[:80]}")

        # Take screenshot for debugging
        screenshot = story_path / f"salt_submit_{datetime.now().strftime('%Y%m%d_%H%M')}.png"
        page.screenshot(path=str(screenshot))
        print(f"[SCREENSHOT] {screenshot}")
        print("[NEXT] 检查截图→找到投稿按钮→手动提交或继续自动化")

        browser.close()
    return True

def main():
    if len(sys.argv) < 2:
        print("用法: python salt_submit.py <story_directory>")
        print("示例: python salt_submit.py path_e_fiction")
        return

    story_dir = sys.argv[1]
    submit_story(story_dir)

if __name__ == "__main__":
    main()
