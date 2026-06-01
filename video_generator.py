#!/usr/bin/env python3
"""
Bija抖音视频生成器 v1.0
避坑文章脚本 → TTS语音 + 文字卡片 + 背景 → MP4短视频

依赖: edge-tts, pillow, ffmpeg
用法: python video_generator.py <script.json> [--output video.mp4]
"""
import json, sys, asyncio, subprocess, tempfile, os
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: pip install pillow"); sys.exit(1)

# ── Config ──
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30
BG_COLOR = (15, 20, 30)       # Dark blue-black
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (57, 186, 230)  # Blue accent
HIGHLIGHT_COLOR = (127, 217, 98)  # Green
WARNING_COLOR = (255, 180, 84)    # Orange
FONT_SIZE_TITLE = 60
FONT_SIZE_BODY = 40
FONT_SIZE_SMALL = 28
FONT_PATH = None  # Auto-detect


def find_font():
    """Find a Chinese-compatible font."""
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",     # 黑体
        "C:/Windows/Fonts/simsun.ttc",     # 宋体
        "C:/Windows/Fonts/STSONG.TTF",     # 华文宋体
    ]
    for f in candidates:
        if Path(f).exists():
            return f
    return None


async def generate_tts(text, output_path, voice="zh-CN-XiaoxiaoNeural"):
    """Generate TTS audio using edge-tts."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return output_path


def get_audio_duration(audio_path):
    """Get audio duration in seconds using ffprobe."""
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
    ], capture_output=True, text=True)
    return float(result.stdout.strip())


def create_frame(width, height, bg_color, text_lines, font_path, duration_sec):
    """Create a single frame image with text."""
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype(font_path, FONT_SIZE_TITLE)
        font_body = ImageFont.truetype(font_path, FONT_SIZE_BODY)
        font_small = ImageFont.truetype(font_path, FONT_SIZE_SMALL)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()

    y = 200
    line_height_body = FONT_SIZE_BODY + 20
    line_height_title = FONT_SIZE_TITLE + 30

    for line_info in text_lines:
        text = line_info.get('text', '')
        color_name = line_info.get('color', 'white')
        size = line_info.get('size', 'body')

        if color_name == 'accent': color = ACCENT_COLOR
        elif color_name == 'green': color = HIGHLIGHT_COLOR
        elif color_name == 'orange': color = WARNING_COLOR
        else: color = TEXT_COLOR

        font = font_title if size == 'title' else (font_small if size == 'small' else font_body)

        # Word wrap
        max_width = width - 120
        lines = wrap_text(text, font, draw, max_width)

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw.text((x, y), line, fill=color, font=font)
            y += line_height_body if size != 'title' else line_height_title

        y += 20  # Extra gap between sections

    return img


def wrap_text(text, font, draw, max_width):
    """Simple word wrap for Chinese text."""
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] > max_width:
            if current_line:
                lines.append(current_line)
            current_line = char
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)
    return lines


def build_script_from_douyin_json(script_path):
    """Convert .douyin.json to video script with timed slides."""
    script = json.loads(Path(script_path).read_text(encoding='utf-8'))
    title = script.get('title', 'DFT避坑')[:50]
    hashtags = script.get('hashtags', [])

    # Build slides
    slides = [
        # Slide 1: Title card (3 seconds, no TTS)
        {
            'duration': 3.0,
            'tts': '',
            'lines': [
                {'text': '计算化学避坑指南', 'size': 'title', 'color': 'accent'},
                {'text': '', 'size': 'body'},
                {'text': title.replace('#', '').strip(), 'size': 'body', 'color': 'green'},
            ]
        },
        # Slide 2: Hook (read by TTS)
        {
            'duration': 8.0,
            'tts': '做DFT计算的都知道，一行命令就能跑出结果。但跑出来的数字到底对不对？审稿人问你验证过网格收敛吗的时候，你慌不慌？',
            'lines': [
                {'text': '你跑的结果真的对吗？', 'size': 'title', 'color': 'orange'},
                {'text': '', 'size': 'body'},
                {'text': '代码能跑 ≠ 结果正确', 'size': 'body'},
                {'text': '审稿人5个角度就能推翻你的结论', 'size': 'body', 'color': 'accent'},
            ]
        },
        # Slide 3: Problem
        {
            'duration': 10.0,
            'tts': '我审过七篇用DFT计算做核心论据的稿子。其中四篇的数字在收敛测试后发生了定性反转。更可怕的是，同一体系用不同方法算出来的结果，三种方法说A方向，另外三种说B方向。',
            'lines': [
                {'text': '真实审稿经历', 'size': 'title', 'color': 'orange'},
                {'text': '', 'size': 'body'},
                {'text': '7篇稿子 → 4篇结果定性反转', 'size': 'body', 'color': 'accent'},
                {'text': '6种方法 → 3种给相反方向', 'size': 'body', 'color': 'accent'},
            ]
        },
        # Slide 4: Key insight
        {
            'duration': 12.0,
            'tts': '核心问题就一个。你的参数选择是经过验证的最优值，还是师兄给的默认值？如果是默认值，审稿人只需要换一套参数重跑，就能推翻你的全部结论。',
            'lines': [
                {'text': '核心问题', 'size': 'title', 'color': 'orange'},
                {'text': '', 'size': 'body'},
                {'text': '你的参数 = 经验证的最优值？', 'size': 'body'},
                {'text': '还是师兄给的默认值？', 'size': 'body', 'color': 'accent'},
            ]
        },
        # Slide 5: Solution
        {
            'duration': 15.0,
            'tts': '解决方法很简单。投稿前做好三件事。第一，收敛测试放在SI里，不放正文。第二，每种分析方法至少用两种方法交叉验证。第三，每个核心结论至少有三条独立证据支撑。做好这三件事，审稿人找不到可以质疑的角度。',
            'lines': [
                {'text': '投稿前三件事', 'size': 'title', 'color': 'green'},
                {'text': '', 'size': 'body'},
                {'text': '1. 收敛测试放SI', 'size': 'body'},
                {'text': '2. 双方法交叉验证', 'size': 'body'},
                {'text': '3. 三证据支撑每个结论', 'size': 'body'},
            ]
        },
        # Slide 6: CTA
        {
            'duration': 5.0,
            'tts': '关注我，每天一个DFT避坑技巧。评论区告诉我，你踩过什么坑？',
            'lines': [
                {'text': '每天一个避坑技巧', 'size': 'title', 'color': 'accent'},
                {'text': '', 'size': 'body'},
                {'text': '💬 评论区: 你踩过什么坑？', 'size': 'body', 'color': 'green'},
            ]
        },
    ]

    return {
        'title': title,
        'hashtags': hashtags,
        'slides': slides,
        'total_duration': sum(s['duration'] for s in slides),
    }


async def generate_video(script_path, output_path=None):
    """Generate a complete video from a douyin script."""
    script_path = Path(script_path)
    if output_path is None:
        output_path = script_path.with_suffix('.mp4')

    font_path = find_font()
    if not font_path:
        print("[WARN] No Chinese font found, text may not render correctly")
        font_path = "C:/Windows/Fonts/msyh.ttc"  # Default

    plan = build_script_from_douyin_json(script_path)
    print(f"Generating: {plan['title'][:50]}")
    print(f"Duration: {plan['total_duration']:.0f}s, Slides: {len(plan['slides'])}")

    # Create temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        audio_files = []
        frame_files = []

        # Generate TTS audio for each slide
        for i, slide in enumerate(plan['slides']):
            if slide['tts']:
                audio_path = tmpdir / f"audio_{i:02d}.mp3"
                await generate_tts(slide['tts'], str(audio_path))
                actual_duration = get_audio_duration(audio_path)
                # Extend slide duration if TTS is longer
                if actual_duration > slide['duration']:
                    slide['duration'] = actual_duration + 0.5
                audio_files.append((i, str(audio_path)))

        # Generate frames for each slide
        for i, slide in enumerate(plan['slides']):
            duration = slide['duration']
            num_frames = max(1, int(duration * FPS))
            frame_path = tmpdir / f"frame_{i:02d}.png"

            img = create_frame(VIDEO_WIDTH, VIDEO_HEIGHT, BG_COLOR,
                              slide['lines'], font_path, duration)
            img.save(str(frame_path))
            frame_files.append((i, str(frame_path), duration))

        # Build ffmpeg command
        # Strategy: Create video segments for each slide, then concat
        segment_files = []
        for i, frame_path, duration in frame_files:
            seg_path = tmpdir / f"seg_{i:02d}.mp4"

            # Check if there's audio for this slide
            audio_for_slide = None
            for ai, ap in audio_files:
                if ai == i:
                    audio_for_slide = ap
                    break

            if audio_for_slide:
                cmd = [
                    "ffmpeg", "-y", "-loop", "1", "-i", frame_path,
                    "-i", audio_for_slide,
                    "-c:v", "libx264", "-t", str(duration),
                    "-pix_fmt", "yuv420p", "-vf",
                    f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}",
                    "-c:a", "aac", "-shortest",
                    str(seg_path)
                ]
            else:
                # Silent segment
                cmd = [
                    "ffmpeg", "-y", "-loop", "1", "-i", frame_path,
                    "-c:v", "libx264", "-t", str(duration),
                    "-pix_fmt", "yuv420p", "-vf",
                    f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}",
                    str(seg_path)
                ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                print(f"  ffmpeg error on seg {i}: {result.stderr[-200:]}")
                continue
            segment_files.append(str(seg_path))

        if not segment_files:
            print("[FAIL] No video segments generated")
            return None

        # Concat all segments
        concat_list = tmpdir / "concat.txt"
        concat_list.write_text("\n".join(
            f"file '{s}'" for s in segment_files
        ))

        final_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list), "-c", "copy",
            str(output_path)
        ]
        result = subprocess.run(final_cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            size_mb = Path(output_path).stat().st_size / 1024 / 1024
            print(f"[OK] {output_path} ({size_mb:.1f}MB, {plan['total_duration']:.0f}s)")
            return str(output_path)
        else:
            print(f"[FAIL] Concat error: {result.stderr[-200:]}")
            return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python video_generator.py <script.douyin.json>")
        print("       python video_generator.py --batch   (generate all)")
        return

    if sys.argv[1] == "--batch":
        content_dir = Path(__file__).parent / "content"
        scripts = sorted(content_dir.glob("*.douyin.json"))
        print(f"Batch generating {len(scripts)} videos...")
        for s in scripts:
            asyncio.run(generate_video(s))
    else:
        script_path = sys.argv[1]
        output = sys.argv[2] if len(sys.argv) > 2 else None
        asyncio.run(generate_video(script_path, output))


if __name__ == "__main__":
    main()
