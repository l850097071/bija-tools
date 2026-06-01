#!/usr/bin/env python3
"""
bija-tools 自动化发布与推广引擎
- 内容格式化（知乎/Reddit/Dev.to/公众号）
- 发布队列管理
- 推广文案生成
- 效果追踪
用法: python auto_publisher.py format <article.md> <platform>
      python auto_publisher.py queue --list
      python auto_publisher.py stats
"""
import json
import argparse
from pathlib import Path
from datetime import datetime

CONTENT_DIR = Path(__file__).parent / "content"
QUEUE_FILE = Path(__file__).parent / "publish_queue.json"
STATS_FILE = Path(__file__).parent / "publish_stats.json"

PLATFORM_FORMATS = {
    "zhihu": {
        "max_title": 50,
        "best_sections": ["避坑", "踩坑", "错误", "陷阱", "实战"],
        "tags_template": "#计算化学 #DFT #VASP #{topic}",
        "disclaimer": "\n\n---\n*本文由Bija辅助生成，经人工深度审核。欢迎讨论交流。*"
    },
    "reddit": {
        "max_title": 300,
        "subreddits": ["comp_chem", "chemistry", "compmatphys", "HPC"],
        "flair_map": {"tutorial": "Tutorial", "discussion": "Discussion", "resource": "Resource"},
        "footer": "\n\n---\n*Cross-posted from bija-tools project. [GitHub](https://github.com/l850097071/bija-tools)*"
    },
    "devto": {
        "max_title": 128,
        "tags": ["computationalchemistry", "dft", "vasp", "materials", "python"],
        "canonical_url": "https://github.com/l850097071/bija-tools"
    },
    "xiaohongshu": {
        "max_title": 20,
        "max_body": 1000,
        "best_format": "图文",
        "hashtags": "#DFT计算 #科研日常 #计算化学 #避坑指南"
    }
}


def format_for_platform(content_path, platform):
    """Format a markdown article for a specific platform."""
    content = Path(content_path).read_text(encoding="utf-8")
    lines = content.split("\n")

    # Extract title
    title = lines[0].replace("# ", "").strip() if lines[0].startswith("#") else Path(content_path).stem
    body = "\n".join(lines[1:]).strip()
    cfg = PLATFORM_FORMATS.get(platform, {})

    if platform == "zhihu":
        # Truncate title if needed
        if len(title) > cfg["max_title"]:
            title = title[:cfg["max_title"]-3] + "..."
        # Add tags
        topic = title.split("：")[-1] if "：" in title else title
        body += cfg["disclaimer"]
        return {"title": title, "body": body, "tags": cfg["tags_template"].format(topic=topic)[:100]}

    elif platform == "reddit":
        body += cfg["footer"]
        return {
            "title": title,
            "body": body,
            "subreddit": cfg["subreddits"][0],
            "flair": "Tutorial"
        }

    elif platform == "devto":
        return {
            "title": title,
            "body": body,
            "tags": cfg["tags"],
            "canonical_url": cfg["canonical_url"]
        }

    elif platform == "xiaohongshu":
        # Split long article into multiple short posts
        chunks = []
        current_chunk = ""
        for para in body.split("\n\n"):
            if len(current_chunk) + len(para) < cfg["max_body"]:
                current_chunk += para + "\n\n"
            else:
                chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        return {"title": title[:cfg["max_title"]], "chunks": chunks, "hashtags": cfg["hashtags"]}

    return {"title": title, "body": body}


def load_queue():
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    return []


def save_queue(queue):
    QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_format(args):
    """Format content for a platform."""
    result = format_for_platform(args.file, args.platform)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # Save formatted output
    out_path = Path(args.file).with_suffix(f".{args.platform}.json")
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[SAVED] {out_path}")


def cmd_add_queue(args):
    """Add article to publish queue."""
    queue = load_queue()
    content_path = Path(args.file)
    if not content_path.exists():
        print(f"[ERROR] File not found: {args.file}")
        return

    queue.append({
        "file": str(content_path),
        "platforms": args.platforms.split(","),
        "status": "pending",
        "added": datetime.now().isoformat(),
        "priority": args.priority or "normal"
    })
    save_queue(queue)
    print(f"[QUEUE] Added: {args.file} → {args.platforms}")


def cmd_list_queue(args):
    """List publishing queue."""
    queue = load_queue()
    if not queue:
        print("[EMPTY] No items in queue")
        return
    print(f"\n{'='*60}")
    print(f"  Publishing Queue ({len(queue)} items)")
    print(f"{'='*60}")
    for i, item in enumerate(queue):
        status_icon = {"pending": "[...]", "published": "[OK]", "failed": "[FAIL]"}.get(item["status"], "[?]")
        print(f"  {status_icon} [{i+1}] {Path(item['file']).name[:50]} → {item['platforms']}")


def cmd_stats(args):
    """Show publishing statistics."""
    # Count content
    zhihu_dir = Path(__file__).parent / "path_b_ai_content"
    content_dir = Path(__file__).parent / "content"
    zhihu_count = len(list(zhihu_dir.glob("知乎*.md"))) if zhihu_dir.exists() else 0
    content_count = len(list(content_dir.glob("zhihu_*.md"))) if content_dir.exists() else 0
    en_count = len(list(content_dir.glob("en_*.md"))) if content_dir.exists() else 0

    print(f"\n{'='*60}")
    print(f"  Bija-变现 内容资产统计 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
    print(f"  知乎文章(早期): {zhihu_count} 篇")
    print(f"  知乎文章(避坑): {content_count} 篇")
    print(f"  英文内容: {en_count} 篇")
    print(f"  总计: {zhihu_count + content_count} 篇中文 + {en_count} 篇英文")
    print(f"\n  估算资产:")
    avg_words = 3500
    total_words = (zhihu_count + content_count) * avg_words
    print(f"    总字数: ~{total_words:,} 字")
    print(f"    估算创作时间: ~{total_words // 500} 小时 (AI辅助)")
    print(f"    如果致知计划发布: ~¥{(zhihu_count + content_count) * 3}-{(zhihu_count + content_count) * 8} 盐粒/篇")


def main():
    parser = argparse.ArgumentParser(description="bija-tools 自动化发布与推广引擎")
    sub = parser.add_subparsers(dest="cmd")

    p_fmt = sub.add_parser("format", help="Format content for platform")
    p_fmt.add_argument("file", help="Markdown file")
    p_fmt.add_argument("platform", choices=["zhihu", "reddit", "devto", "xiaohongshu"])

    p_add = sub.add_parser("add", help="Add to publish queue")
    p_add.add_argument("file", help="Markdown file")
    p_add.add_argument("--platforms", "-p", default="zhihu", help="Target platforms (comma-separated)")
    p_add.add_argument("--priority", choices=["high", "normal", "low"])

    p_list = sub.add_parser("list", help="List publish queue")

    p_stats = sub.add_parser("stats", help="Content statistics")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return

    {"format": cmd_format, "add": cmd_add_queue, "list": cmd_list_queue, "stats": cmd_stats}[args.cmd](args)


if __name__ == "__main__":
    main()
