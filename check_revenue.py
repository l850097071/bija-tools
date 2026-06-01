#!/usr/bin/env python3
"""Check知乎 articles and counts."""
import json, urllib.request
from pathlib import Path

config = json.loads((Path.home() / '.config' / 'multi-publisher' / 'config.json').read_text('utf-8'))
cookies = config['zhihu']['cookies']
cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())
headers = {
    'Cookie': cookie_str,
    'User-Agent': 'Mozilla/5.0',
    'X-Requested-With': 'fetch',
}

endpoints = [
    ('Articles Count', 'https://www.zhihu.com/api/v4/members/bija?include=articles_count,voteup_count,follower_count'),
    ('Creator Stats', 'https://api.zhihu.com/creator/statistics'),
    ('Creator Growth', 'https://api.zhihu.com/creator/growth'),
]

for name, url in endpoints:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            print(f'--- {name} ---')
            print(json.dumps(data, ensure_ascii=False, indent=2)[:800])
            print()
    except Exception as e:
        print(f'--- {name}: {e} ---\n')
