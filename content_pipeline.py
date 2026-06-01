#!/usr/bin/env python3
"""
Bija-变现 内容管线管理工具
用法:
  python content_pipeline.py index       → 扫描所有知乎文章，生成索引
  python content_pipeline.py stats       → 内容矩阵统计
  python content_pipeline.py publish N   → 标记第N篇为"待宿主审核"
  python content_pipeline.py queue       → 查看发布队列
  python content_pipeline.py gap         → 检测选题空白领域
"""
import sys, os, json, re
from pathlib import Path
from datetime import datetime
from collections import Counter

CONTENT_DIR = Path(__file__).parent / "path_b_ai_content"
INDEX_FILE = Path(__file__).parent / "content_index.json"
PUBLISH_QUEUE = Path(__file__).parent / "publish_queue.json"

# 领域分类关键词
DOMAIN_TAGS = {
    "AI产业": ["产业", "企业", "落地", "Agent"],
    "AI技术": ["协议", "MCP", "A2A", "架构", "模型"],
    "AI政策": ["监管", "政策", "AI法案", "合规"],
    "AI应用": ["工具", "效率", "编程", "自动化"],
    "学术": ["论文", "审稿", "学术", "期刊", "DFT"],
    "变现": ["赚钱", "知识付费", "副业", "变现", "盐粒", "好物", "佣金", "CPS"],
    "创业": ["一人公司", "数字游民", "独立开发者", "超级个体"],
    "开源": ["开源", "GitHub", "HuggingFace", "推广", "DevTool"],
    "医疗": ["医疗", "药物", "诊断", "健康"],
    "硬件": ["芯片", "GPU", "算力", "机器人"],
    "安全": ["安全", "攻击", "防御", "黑客"],
    "能源": ["环境", "碳排放", "电力", "能源"],
    "法律": ["律师", "法律", "合规", "法务"],
    "制造": ["制造", "工厂", "工业", "数字孪生"],
    "内容创作": ["视频生成", "Sora", "自媒体", "创作", "涨粉"],
    "其他": []
}

def extract_metadata(filepath):
    """Extract title, word count, and domain from a知乎 article"""
    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")

    # Extract title (first # heading)
    title = ""
    for line in lines:
        if line.startswith("# ") and "知乎" in line:
            title = line.replace("# ", "").strip()
            break

    # Word count (approximate: Chinese chars + English words)
    text = re.sub(r'[#*>\-\|\s]', ' ', content)
    chinese_chars = len(re.findall(r'[一-鿿]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    word_count = chinese_chars + english_words

    # Domain detection
    domains = []
    content_lower = content.lower()
    for domain, keywords in DOMAIN_TAGS.items():
        if domain == "其他":
            continue
        score = sum(1 for kw in keywords if kw.lower() in content_lower)
        if score >= 2:
            domains.append(domain)
    if not domains:
        domains = ["其他"]

    # Tags
    tags = []
    tag_section = False
    for line in lines:
        if "**标签**" in line or "**发布平台**" in line:
            tag_section = True
            continue
        if tag_section and line.startswith("---"):
            break
        if tag_section and line.startswith("**标签**"):
            tag_text = line.replace("**标签**：", "").replace("**标签**:", "").strip()
            tags = [t.strip().lstrip("#") for t in tag_text.split("#") if t.strip()]

    return {
        "file": filepath.name,
        "title": title,
        "word_count": word_count,
        "domains": domains,
        "tags": tags,
        "path": str(filepath.relative_to(CONTENT_DIR.parent))
    }

def cmd_index():
    """Scan all知乎 articles and build index"""
    articles = []
    for md_file in sorted(CONTENT_DIR.glob("知乎*.md")):
        try:
            meta = extract_metadata(md_file)
            articles.append(meta)
        except Exception as e:
            print(f"  [SKIP] {md_file.name}: {e}")

    INDEX_FILE.write_text(json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[INDEX] 索引完成: {len(articles)} 篇知乎文章")
    total_words = sum(a["word_count"] for a in articles)
    print(f"[STATS] 总字数: ~{total_words:,}")
    print(f"[STATS] 平均字数: ~{total_words // len(articles):,}/篇")
    return articles

def cmd_stats():
    """Print content matrix statistics"""
    if not INDEX_FILE.exists():
        print("[ERROR] 先运行 python content_pipeline.py index")
        return

    articles = json.loads(INDEX_FILE.read_text(encoding="utf-8"))

    # Domain distribution
    domain_count = Counter()
    for a in articles:
        for d in a["domains"]:
            domain_count[d] += 1

    print(f"\n{'='*60}")
    print(f"  Bija-变现 知乎内容矩阵 · {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*60}")
    print(f"  总文章数: {len(articles)}")
    print(f"  总字数: ~{sum(a['word_count'] for a in articles):,}")
    print(f"\n  --- 领域分布 ---")
    for domain, count in domain_count.most_common():
        bar = "#" * count
        print(f"  {domain:<12} {count:>3} {bar}")

    # Word count distribution
    ranges = [(0, 2000, "短文<2000"), (2000, 2600, "标准2000-2600"), (2600, 3000, "长文2600-3000"), (3000, 99999, "超长3000+")]
    print(f"\n  --- 字数分布 ---")
    for lo, hi, label in ranges:
        count = sum(1 for a in articles if lo <= a["word_count"] < hi)
        print(f"  {label}: {count}篇")

    # Latest articles
    print(f"\n  --- 最新5篇 ---")
    for a in articles[-5:]:
        print(f"  {a['file'][:40]:<42} {a['word_count']:>5,}字  {', '.join(a['domains'][:2])}")

def cmd_gap():
    """Detect content gaps vs coverage goals"""
    covered = set()
    if INDEX_FILE.exists():
        articles = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        for a in articles:
            for d in a["domains"]:
                covered.add(d)

    all_domains = set(DOMAIN_TAGS.keys()) - {"其他"}
    gaps = all_domains - covered

    print(f"\n  --- 选题空白检测 ---")
    print(f"  已覆盖: {len(covered)} 领域: {', '.join(sorted(covered))}")
    if gaps:
        print(f"  空白领域: {', '.join(sorted(gaps))}")
    else:
        print(f"  [OK] 所有定义领域已覆盖!")

    # Suggest next topics
    print(f"\n  --- 建议选题方向 ---")
    suggestions = [
        ("AI+教育", "教育领域暂无, 知乎18(学习)不算系统覆盖"),
        ("AI+金融量化", "待明天与宿主讨论AI炒股"),
        ("AI+农业/食品", "完全空白"),
        ("AI开源模型选型指南", "知乎13/20部分覆盖, 但缺系统对比"),
    ]
    for topic, reason in suggestions:
        print(f"  [{topic}] {reason}")

def cmd_queue():
    """Show publishing queue"""
    if PUBLISH_QUEUE.exists():
        queue = json.loads(PUBLISH_QUEUE.read_text(encoding="utf-8"))
        print(f"\n  --- 发布队列 ({len(queue)}篇) ---")
        for i, item in enumerate(queue):
            status_icon = {"pending": "[...]", "approved": "[OK]", "published": "[OUT]"}.get(item.get("status", "pending"), "[?]")
            print(f"  {status_icon} [{i+1}] {item.get('title', '?')[:60]}")
    else:
        print("[EMPTY] 发布队列为空, 运行 'python content_pipeline.py publish N' 添加")

def cmd_publish(n):
    """Add article N to publish queue"""
    if not INDEX_FILE.exists():
        print("[ERROR] 先运行 index")
        return

    articles = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    if n < 1 or n > len(articles):
        print(f"[ERROR] 序号 {n} 超出范围 (1-{len(articles)})")
        return

    article = articles[n-1]
    queue = []
    if PUBLISH_QUEUE.exists():
        queue = json.loads(PUBLISH_QUEUE.read_text(encoding="utf-8"))

    queue.append({
        "title": article["title"],
        "file": article["file"],
        "path": article["path"],
        "word_count": article["word_count"],
        "status": "pending",
        "added": datetime.now().isoformat()
    })

    PUBLISH_QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[QUEUE] 已加入发布队列: {article['title'][:60]}")
    print(f"[QUEUE] 队列共 {len(queue)} 篇待处理")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "index":
        cmd_index()
    elif cmd == "stats":
        cmd_stats()
    elif cmd == "gap":
        cmd_gap()
    elif cmd == "queue":
        cmd_queue()
    elif cmd == "publish":
        if len(sys.argv) < 3:
            print("用法: python content_pipeline.py publish <序号>")
            return
        cmd_publish(int(sys.argv[2]))
    else:
        print(f"[ERROR] 未知命令: {cmd}")
        print(__doc__)

if __name__ == "__main__":
    main()
