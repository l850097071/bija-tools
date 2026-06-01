#!/usr/bin/env python3
"""
Bija抖音自动发布管线 v1.0
- douyin-mcp-server v2.0.0 + TypeScript已编译
- douyin_uploader.mjs 桥接脚本
- 首次宿主扫码登录(30s) → 后续全自动

用法:
  python douyin_pipeline.py status             → 检查登录状态
  python douyin_pipeline.py login              → 扫码登录抖音(需宿主30秒)
  python douyin_pipeline.py convert <md>       → 避坑文章→视频脚本
  python douyin_pipeline.py upload <video>     → 上传视频到抖音(需已登录)
  python douyin_pipeline.py plan               → 查看发布计划
"""
import json, sys, subprocess
from pathlib import Path
from datetime import datetime

BRIDGE = Path(__file__).parent / "douyin_uploader.mjs"


def run_bridge(action, *args):
    """Run the douyin_uploader.mjs bridge script."""
    cmd = ["node", str(BRIDGE), action] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def cmd_status():
    code, out, err = run_bridge("status")
    if code == 0:
        try:
            data = json.loads(out)
            if data.get("isValid"):
                print(f"[OK] 已登录抖音: {data.get('user', 'unknown')}")
                return True
            else:
                print(f"[NOT LOGGED IN] 需要扫码登录: python douyin_pipeline.py login")
                return False
        except json.JSONDecodeError:
            print(f"[RAW] {out}")
    else:
        print(f"[ERR] {err}")
    return False


def cmd_login():
    print("Opening browser for抖音 QR code login...")
    print("请在30秒内用抖音App扫描浏览器中的二维码")
    print()
    code, out, err = run_bridge("login")
    if code == 0:
        try:
            data = json.loads(out)
            if data.get("success"):
                print(f"[OK] 登录成功! 用户: {data.get('user')}")
                print("Cookie已保存，后续上传无需重复登录。")
            else:
                print(f"[FAIL] {data.get('error', out)}")
        except json.JSONDecodeError:
            # Might be non-JSON output during browser login
            print(out)
    else:
        print(f"[FAIL] {err or out}")


def cmd_convert(args):
    """Convert markdown article to抖音 video script."""
    article = Path(args.file)
    if not article.exists():
        print(f"[ERROR] {args.file} not found"); return

    content = article.read_text(encoding='utf-8')
    title = content.split('\n')[0].replace('# ', '').strip()[:80]

    # Detect topic
    if 'Bader' in content: topic = 'Bader电荷分析'
    elif '吸附' in content: topic = '吸附能计算'
    elif '能带' in content: topic = '能带结构'
    elif 'DOS' in content or '态密度' in content: topic = '态密度DOS'
    elif '声子' in content or '振动' in content: topic = '振动频率/声子谱'
    elif 'NEB' in content or '过渡态' in content: topic = '过渡态搜索'
    elif '功函数' in content: topic = '功函数'
    elif '范德华' in content: topic = '范德华修正'
    elif 'DFT+U' in content: topic = 'DFT+U'
    elif 'bug' in content.lower(): topic = 'VASP软件bug'
    else: topic = 'DFT计算'

    script = {
        "title": f"#{topic}避坑 #{'计算化学'}",
        "description": f"做DFT计算的都遇到过{topic}的问题。这个避坑指南帮你避开最常见的10个陷阱。\n\n#计算化学 #DFT #科研 #论文 #避坑",
        "hashtags": ["计算化学", "DFT", "科研", "论文", "避坑指南"],
        "source": str(article),
        "topic": topic,
    }

    out_path = article.with_suffix('.douyin.json')
    out_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"[OK] {out_path}")
    print(f"  Title: {script['title'][:60]}")
    print(f"  Topic: {topic}")


def cmd_upload(args):
    """Upload video to抖音."""
    video = args.file if hasattr(args, 'file') else args
    if isinstance(video, str):
        video_path = Path(video)
    else:
        video_path = Path(args.file)

    if not video_path.exists():
        print(f"[ERROR] Video not found: {video_path}")
        print("First convert article to script, then create video, then upload.")
        return

    # Load associated script if exists
    script_path = video_path.with_suffix('.douyin.json')
    title = ""
    tags = '["计算化学","DFT","科研","知识"]'
    if script_path.exists():
        s = json.loads(script_path.read_text(encoding='utf-8'))
        title = s.get('title', '')[:50]
        tags = json.dumps(s.get('hashtags', []))

    print(f"Uploading: {video_path.name}")
    code, out, err = run_bridge("upload", str(video_path.resolve()), title, tags)
    if code == 0:
        try:
            data = json.loads(out)
            if data.get("success"):
                print(f"[PUBLISHED] 抖音发布成功!")
            else:
                print(f"[FAIL] {data.get('error', out)}")
        except json.JSONDecodeError:
            print(f"[RAW] {out[:300]}")
    else:
        print(f"[FAIL] {err or out}")


def cmd_plan():
    """Show抖音 publishing plan."""
    content_dir = Path(__file__).parent / "content"
    pitfall_articles = sorted(content_dir.glob("zhihu_*避坑*.md"))
    print(f"""
╔══════════════════════════════════════════════╗
║  Bija抖音发布计划 v1.0                      ║
║  避坑系列 {len(pitfall_articles)}篇可转为短视频              ║
╚══════════════════════════════════════════════╝

Pipeline:
  1. python douyin_pipeline.py login           (一次性, 30秒扫码)
  2. python douyin_pipeline.py convert <md>    (文章→脚本)
  3. [创建视频: 文字转语音+画面, 工具如剪映/CapCut]
  4. python douyin_pipeline.py upload <video>  (自动发布)

Monetization:
  - 抖音中视频计划: 1分钟以上视频获流量分成
  - 引流至知乎/GitHub: 视频简介挂链接
  - 知识付费: 积累粉丝→付费社群/课程
  - 品牌合作: DFT/计算化学垂直领域

Content Strategy:
  - 时长: 1-3分钟 (中视频计划最低1分钟)
  - 频率: 每天1-2条
  - 形式: 文字解说+屏幕录制/动画
  - 差异化: 中文互联网唯一DFT避坑短视频账号
""")


def main():
    if len(sys.argv) < 2:
        print("Bija抖音自动发布管线")
        print("  python douyin_pipeline.py status|login|convert|upload|plan")
        return

    cmd = sys.argv[1]
    if cmd == "status": cmd_status()
    elif cmd == "login": cmd_login()
    elif cmd == "plan": cmd_plan()
    elif cmd == "convert" and len(sys.argv) > 2:
        import argparse
        p = argparse.Namespace(file=sys.argv[2])
        cmd_convert(p)
    elif cmd == "upload" and len(sys.argv) > 2:
        import argparse
        p = argparse.Namespace(file=sys.argv[2])
        cmd_upload(p)
    else:
        print("Unknown command. Try: status, login, convert, upload, plan")


if __name__ == "__main__":
    main()
