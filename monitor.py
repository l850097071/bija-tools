#!/usr/bin/env python3
"""
知乎自动监控+互动 — 评论回复 + 问答发现
用法: python monitor.py comments  → 检查已发文章的新评论
      python monitor.py questions → 搜索相关DFT/计算化学新问题
      python monitor.py auto      → 自动回复新评论(需AI生成回复)
"""
import sys, os, json, time, re
from pathlib import Path
from datetime import datetime

MONITOR_DIR = Path(__file__).parent / "monitor_data"
MONITOR_DIR.mkdir(exist_ok=True)

def load_cookies():
    """Load知乎 cookies saved by multi-publisher"""
    cookie_file = Path.home() / ".mpub" / "cookies" / "zhihu.json"
    if cookie_file.exists():
        return json.loads(cookie_file.read_text(encoding="utf-8"))
    return None

def get_browser_context(playwright):
    """Create browser context with existing知乎 cookies"""
    cookies = load_cookies()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    if cookies:
        context.add_cookies(cookies)
    return browser, context

def check_new_comments():
    """Check our published articles for new unread comments"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SETUP] pip install playwright && playwright install chromium")
        return []

    new_comments = []
    with sync_playwright() as p:
        browser, context = get_browser_context(p)
        page = context.new_page()

        # Go to creator dashboard
        page.goto("https://www.zhihu.com/creator/contents", timeout=30000)
        page.wait_for_timeout(3000)

        # Find recent articles
        articles = page.query_selector_all("[class*='ContentItem']")
        for article in articles[:5]:  # Check latest 5 articles
            try:
                title_el = article.query_selector("a[class*='title']")
                if not title_el:
                    continue
                title = title_el.inner_text()
                link = title_el.get_attribute("href")

                # Navigate to article
                article_page = context.new_page()
                article_page.goto(link, timeout=30000)
                article_page.wait_for_timeout(2000)

                # Find comments
                comments = article_page.query_selector_all("[class*='CommentItem']")
                for comment in comments:
                    try:
                        content_el = comment.query_selector("[class*='content']")
                        author_el = comment.query_selector("[class*='author']")
                        if content_el and author_el:
                            content = content_el.inner_text().strip()
                            author = author_el.inner_text().strip()
                            # Simple dedup: skip already-processed
                            cid = f"{author}:{content[:50]}"
                            new_comments.append({
                                "article": title,
                                "author": author,
                                "content": content,
                                "cid": cid,
                                "time": datetime.now().isoformat()
                            })
                    except:
                        continue
                article_page.close()
            except Exception as e:
                print(f"  [SKIP] {e[:80]}")
                continue

        browser.close()

    # Dedup and save
    seen = set()
    fresh = []
    history_file = MONITOR_DIR / "comment_history.jsonl"
    if history_file.exists():
        for line in history_file.read_text(encoding="utf-8").splitlines():
            try:
                seen.add(json.loads(line)["cid"])
            except:
                pass

    for c in new_comments:
        if c["cid"] not in seen:
            fresh.append(c)
            seen.add(c["cid"])

    if fresh:
        with open(history_file, "a", encoding="utf-8") as f:
            for c in fresh:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")

    return fresh

def search_questions():
    """Search for new知乎 questions about DFT/计算化学/VASP"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SETUP] pip install playwright")
        return []

    topics = ["DFT", "VASP", "计算化学", "第一性原理", "自由能计算", "催化计算"]
    questions = []

    with sync_playwright() as p:
        browser, context = get_browser_context(p)
        page = context.new_page()

        for topic in topics[:3]:  # Limit to avoid rate limiting
            try:
                search_url = f"https://www.zhihu.com/search?type=content&q={topic}&time_interval=week"
                page.goto(search_url, timeout=30000)
                page.wait_for_timeout(2000)

                items = page.query_selector_all("[class*='List-item']")
                for item in items[:10]:
                    try:
                        title_el = item.query_selector("a[class*='title'], span[class*='Highlight']")
                        if title_el:
                            title = title_el.inner_text().strip()
                            questions.append({"topic": topic, "title": title, "time": datetime.now().isoformat()})
                    except:
                        continue
            except:
                continue

        browser.close()
    return questions

def main():
    if len(sys.argv) < 2:
        print("用法: python monitor.py comments|questions|auto")
        print("  comments  → 检查新评论")
        print("  questions → 搜索相关新问题")
        print("  auto      → 自动回复新评论(需先生成回复)")
        return

    cmd = sys.argv[1]

    if cmd == "comments":
        print("[MONITOR] 检查新评论...")
        comments = check_new_comments()
        if comments:
            print(f"[NEW] {len(comments)} 条新评论:")
            for c in comments:
                print(f"  [{c['article'][:30]}...] {c['author']}: {c['content'][:80]}")
            # Save for Bija to generate replies
            outfile = MONITOR_DIR / f"pending_comments_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
            outfile.write_text(json.dumps(comments, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[SAVED] {outfile}")
        else:
            print("[OK] 无新评论")

    elif cmd == "questions":
        print("[MONITOR] 搜索新问题...")
        qs = search_questions()
        if qs:
            print(f"[FOUND] {len(qs)} 个相关问题:")
            for q in qs[:10]:
                print(f"  [{q['topic']}] {q['title'][:80]}")
            outfile = MONITOR_DIR / f"pending_questions_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
            outfile.write_text(json.dumps(qs, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[SAVED] {outfile}")
        else:
            print("[OK] 无新问题")

    elif cmd == "auto":
        print("[AUTO] 自动回复模式")
        # Read pending comments
        pending_files = sorted(MONITOR_DIR.glob("pending_comments_*.json"))
        if not pending_files:
            print("[OK] 无待回复评论")
            return
        latest = pending_files[-1]
        comments = json.loads(latest.read_text(encoding="utf-8"))
        print(f"[TODO] {len(comments)} 条评论待生成AI回复")
        print(f"[NEXT] Bija读取 {latest} → 生成回复 → python monitor.py reply")

if __name__ == "__main__":
    main()
