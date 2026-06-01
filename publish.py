#!/usr/bin/env python3
"""
全自动发布流水线 — 知乎 + Reddit + 更多
用法: python publish.py <platform> <article.md>
      python publish.py all <article.md>
      python publish.py --dry-run <article.md>
"""
import sys, os, json, subprocess, re, argparse
from pathlib import Path
from datetime import datetime

CONFIG_FILE = Path(__file__).parent / "publish_config.json"
LOG_FILE = Path(__file__).parent / "publish_log.jsonl"

def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {"platforms": {}, "default_author": "笔名", "ai_disclaimer": True}

def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

def log_result(platform, article, success, detail=""):
    entry = {"time": datetime.now().isoformat(), "platform": platform, "article": article, "success": success, "detail": detail}
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def parse_article(filepath):
    """Extract title and body from markdown file"""
    text = Path(filepath).read_text(encoding="utf-8")
    lines = text.split("\n")
    title = lines[0].replace("# ", "").strip() if lines[0].startswith("# ") else Path(filepath).stem
    # Remove title line for body
    body = "\n".join(lines[1:]).strip()
    return title, body

def add_disclaimer(body, author="笔名"):
    """Add AI disclaimer and author attribution"""
    disclaimer = f"\n\n---\n*本文由Bija辅助生成，经人工审核。发布于{datetime.now().strftime('%Y-%m-%d')}。*"
    return body + disclaimer

def find_mpub():
    """Find multi-publisher executable, handling npm global bin path"""
    import shutil
    # Try direct first
    mpub = shutil.which("mpub") or shutil.which("mpub.cmd") or shutil.which("mpub.ps1")
    if mpub:
        return mpub
    # Search npm global bin
    npm_root = os.popen("npm root -g").read().strip()
    npm_bin = os.path.join(os.path.dirname(npm_root), "")
    for name in ["mpub.cmd", "mpub.ps1", "mpub"]:
        path = os.path.join(npm_bin, name)
        if os.path.exists(path):
            return path
    return None

def publish_zhihu(filepath, dry_run=False):
    """Publish to 知乎 via multi-publisher CLI"""
    config = load_config()
    zhihu_config = config["platforms"].get("zhihu", {})

    if dry_run:
        title, body = parse_article(filepath)
        return True, f"[DRY RUN] 知乎: '{title}' ({len(body)} chars)"

    # Find multi-publisher
    mpub = find_mpub()
    if not mpub:
        return False, "multi-publisher 未安装。运行: npm install -g multi-publisher"

    # Publish
    try:
        result = subprocess.run(
            [mpub, "publish", "-f", str(Path(filepath).resolve()), "-p", "zhihu"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return True, f"知乎发布成功: {filepath}"
        else:
            return False, f"知乎发布失败: {result.stderr[:200]}"
    except subprocess.TimeoutExpired:
        return False, "知乎发布超时(>120s)"

def publish_reddit(filepath, dry_run=False):
    """Publish to Reddit via PRAW (Python Reddit API Wrapper)"""
    config = load_config()
    reddit_config = config["platforms"].get("reddit", {})

    if dry_run:
        title, body = parse_article(filepath)
        subreddit = reddit_config.get("subreddit", "comp_chem")
        return True, f"[DRY RUN] Reddit r/{subreddit}: '{title}' ({len(body)} chars)"

    if not reddit_config.get("client_id"):
        return False, "Reddit API未配置。运行: python publish.py setup reddit"

    try:
        import praw
        reddit = praw.Reddit(
            client_id=reddit_config["client_id"],
            client_secret=reddit_config["client_secret"],
            user_agent=reddit_config.get("user_agent", "bija-publisher/1.0"),
            username=reddit_config.get("username"),
            password=reddit_config.get("password")
        )
        title, body = parse_article(filepath)
        body = add_disclaimer(body, config.get("default_author", "匿名"))
        subreddit_name = reddit_config.get("subreddit", "comp_chem")
        subreddit = reddit.subreddit(subreddit_name)
        submission = subreddit.submit(title=title, selftext=body, flair_id=reddit_config.get("flair_id"))
        return True, f"Reddit发布成功: https://reddit.com{submission.permalink}"
    except Exception as e:
        return False, f"Reddit发布失败: {str(e)[:200]}"

def setup_platform(platform):
    """Interactive setup for a platform"""
    config = load_config()

    if platform == "zhihu":
        print("=== 知乎- multi-publisher 配置 ===")
        print("1. 安装 Node.js: https://nodejs.org")
        print("2. 安装 multi-publisher: npm install -g multi-publisher")
        print("3. 登录知乎: mpub login -p zhihu")
        print("   (浏览器会自动打开, 扫码登录即可)")
        print("   Cookie会自动保存, 之后无需再登录")
        config["platforms"]["zhihu"] = {
            "tool": "multi-publisher",
            "configured": True,
            "setup_date": datetime.now().isoformat()
        }
        save_config(config)
        print("\n[OK] 知乎配置完成 (需手动执行上面3步)")

    elif platform == "reddit":
        print("=== Reddit PRAW 配置 ===")
        print("1. 访问 https://www.reddit.com/prefs/apps")
        print("2. 点击 'Create App'")
        print("3. 填入: name=bija-publisher, type=script")
        print("4. 获取 client_id (在name下面) 和 client_secret")
        print()
        client_id = input("client_id: ").strip()
        client_secret = input("client_secret: ").strip()
        username = input("Reddit用户名 (留空=匿名): ").strip()
        password = input("Reddit密码 (留空=匿名): ").strip()
        subreddit = input("目标subreddit (默认comp_chem): ").strip() or "comp_chem"

        config["platforms"]["reddit"] = {
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username or None,
            "password": password or None,
            "subreddit": subreddit,
            "user_agent": "bija-publisher/1.0",
            "configured": True,
            "setup_date": datetime.now().isoformat()
        }
        save_config(config)
        print("\n[OK] Reddit配置已保存")
        print("测试发布: python publish.py --dry-run test.md")

    else:
        print(f"未知平台: {platform}. 支持: zhihu, reddit")

def main():
    parser = argparse.ArgumentParser(description="全自动发布流水线")
    parser.add_argument("platform", nargs="?", help="zhihu | reddit | all")
    parser.add_argument("file", nargs="?", help="Markdown文件路径")
    parser.add_argument("--file", "-f", dest="file_arg", help="Markdown文件路径 (与--dry-run配合)")
    parser.add_argument("--dry-run", "-n", action="store_true", help="预览模式，不实际发布")
    parser.add_argument("--setup", "-s", action="store_true", help="配置平台")

    args = parser.parse_args()
    filepath = args.file or args.file_arg

    if args.setup:
        if args.platform:
            setup_platform(args.platform)
        else:
            print("用法: python publish.py --setup <zhihu|reddit>")
        return

    if args.dry_run and filepath:
        platforms = ["zhihu", "reddit"]
    elif args.platform and filepath:
        platforms = ["zhihu", "reddit"] if args.platform == "all" else [args.platform]
    else:
        parser.print_help()
        print("\n示例:")
        print("  python publish.py zhihu article.md")
        print("  python publish.py reddit article.md")
        print("  python publish.py all article.md")
        print("  python publish.py -n -f article.md")
        print("  python publish.py --setup zhihu")
        return

    if not Path(filepath).exists():
        print(f"[FAIL] 文件不存在: {filepath}")
        return
    results = {}

    for p in platforms:
        print(f"[PUB] 发布到 {p}...")
        if p == "zhihu":
            ok, msg = publish_zhihu(filepath, args.dry_run)
        elif p == "reddit":
            ok, msg = publish_reddit(filepath, args.dry_run)
        else:
            ok, msg = False, f"不支持的平台: {p}"

        results[p] = {"success": ok, "message": msg}
        icon = "[OK]" if ok else "[FAIL]"
        print(f"  {icon} {msg}")
        log_result(p, filepath, ok, msg)

    # Summary
    success_count = sum(1 for r in results.values() if r["success"])
    print(f"\n{'[DRY RUN]' if args.dry_run else '[DONE]'}: {success_count}/{len(results)} success")

if __name__ == "__main__":
    main()
