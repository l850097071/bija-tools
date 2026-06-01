"""Publish zhihu draft: try without topic + with title set."""
import json, urllib.request, sys
from pathlib import Path

config = json.loads((Path.home() / '.config/multi-publisher/config.json').read_text('utf-8'))
cookies = config['zhihu']['cookies']
cs = '; '.join(f'{k}={v}' for k, v in cookies.items())
headers = {
    'Cookie': cs, 'User-Agent': 'Mozilla/5.0',
    'X-Requested-With': 'fetch', 'Content-Type': 'application/json',
}

mid = sys.argv[1] if len(sys.argv) > 1 else '2044763924747245295'

# Step 1: Get draft
req = urllib.request.Request(
    f'https://zhuanlan.zhihu.com/api/articles/{mid}/draft', headers=headers)
with urllib.request.urlopen(req) as r:
    draft = json.loads(r.read())

print(f"State: {draft.get('state')}")
print(f"Title: {draft.get('title', '')[:80]}")
print(f"Topics: {draft.get('topics', [])}")

# Step 2: Try publishing directly with body that includes title
# The PATCH might need both title and content to be set for publishing
content = draft.get('content', '')
title = draft.get('title', '')

# Fix title if it's just the filename without extension
if title == '无标题' or not title or len(title) < 3:
    # Try to extract title from content
    import re
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', content)
    if title_match:
        title = title_match.group(1).strip()
        print(f"Extracted title from content: {title[:80]}")
    else:
        title = '计算化学避坑系列'
        print(f"Using default title")

# Method: Try publishing with various payloads
methods = [
    ('publish+title', {'action': 'publish', 'title': title}),
    ('publish+title+content', {'action': 'publish', 'title': title, 'content': content}),
    ('publish_only', {'action': 'publish'}),
    ('put_publish', {'publish': True}),
    ('post_publish', {'status': 'published', 'publish': True}),
]

for name, payload in methods:
    data = json.dumps(payload).encode('utf-8')
    req2 = urllib.request.Request(
        f'https://zhuanlan.zhihu.com/api/articles/{mid}/draft',
        data=data, headers=headers, method='PATCH')
    try:
        with urllib.request.urlopen(req2) as r2:
            resp = json.loads(r2.read())
            print(f"  {name}: OK")

            # Check if actually published
            req3 = urllib.request.Request(
                f'https://zhuanlan.zhihu.com/api/articles/{mid}/draft', headers=headers)
            with urllib.request.urlopen(req3) as r3:
                after = json.loads(r3.read())
                new_state = after.get('state', '')
                new_url = after.get('url', '')
                print(f"    -> state={new_state}, url={new_url}")
                if new_state != 'draft':
                    print(f"    *** PUBLISHED! state changed to: {new_state} ***")
                    sys.exit(0)
    except Exception as e:
        print(f"  {name}: {e}")

# If all methods fail
print(f"\nAll methods tried. Article state: {draft.get('state')}")
print(f"The article may need to be published manually at: https://zhuanlan.zhihu.com/p/{mid}/edit")
