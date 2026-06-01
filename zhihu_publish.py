#!/usr/bin/env python3
"""知乎草稿→公开发布工具。使用存储的Cookie通过知乎API直接发布草稿。"""
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "multi-publisher" / "config.json"


def load_cookies():
    """Load知乎 cookies from mpub config."""
    with open(CONFIG_PATH, encoding='utf-8') as f:
        config = json.load(f)
    return config.get('zhihu', {}).get('cookies', {})


def build_cookie_header(cookies):
    """Build Cookie header string from cookie dict."""
    return '; '.join(f'{k}={v}' for k, v in cookies.items())


def make_request(url, method='GET', cookies=None, data=None, extra_headers=None):
    """Make an HTTP request to知乎 API with cookies."""
    headers = {
        'Cookie': build_cookie_header(cookies),
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'fetch',
        'Origin': 'https://zhuanlan.zhihu.com',
        'Referer': 'https://zhuanlan.zhihu.com/',
    }
    if extra_headers:
        headers.update(extra_headers)

    body = None
    if data:
        body = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode('utf-8')
            return resp.status, content, resp.headers
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        return e.code, error_body, e.headers


def check_auth(cookies):
    """Check if cookies are valid by querying /api/v4/me."""
    status, content, _ = make_request(
        'https://www.zhihu.com/api/v4/me',
        cookies=cookies
    )
    if status == 200:
        data = json.loads(content)
        return True, data.get('name', data.get('id', 'unknown'))
    return False, f'HTTP {status}: {content[:200]}'


def publish_draft(media_id, cookies):
    """Publish a知乎 draft to public.

    Try multiple known知乎 API endpoints for publishing drafts.
    """
    endpoints = [
        # Method 1: PATCH draft with publish action
        ('PATCH', f'https://zhuanlan.zhihu.com/api/articles/{media_id}/draft',
         {'action': 'publish'}),
        # Method 2: PUT draft (some知乎 versions)
        ('PUT', f'https://zhuanlan.zhihu.com/api/articles/{media_id}/draft',
         {'status': 'published'}),
        # Method 3: POST to publish
        ('POST', f'https://zhuanlan.zhihu.com/api/articles/{media_id}/publish',
         {'id': media_id}),
        # Method 4: PATCH the article directly
        ('PATCH', f'https://zhuanlan.zhihu.com/api/articles/{media_id}',
         {'is_published': True, 'publish': True}),
        # Method 5: PUT the article
        ('PUT', f'https://zhuanlan.zhihu.com/api/articles/{media_id}',
         {'is_published': True}),
        # Method 6: Use the /posts endpoint
        ('PUT', f'https://zhuanlan.zhihu.com/api/posts/{media_id}/publish',
         {}),
    ]

    for method, url, data in endpoints:
        status, content, headers = make_request(
            url, method=method, cookies=cookies, data=data,
            extra_headers={'Accept': 'application/json, text/plain, */*'}
        )
        if status in (200, 201, 204):
            return True, f'Published! ({method} {url.split("/")[-2]}/{url.split("/")[-1]})'
        # Log non-404 failures
        if status != 404:
            short = content[:80].replace('\n', ' ')
            print(f'    {method} {url[-50:]}: HTTP {status} -> {short}')

    return False, 'All 6 methods failed'


def publish_article(article_id):
    """Alternative: Create and immediately publish via the articles endpoint."""
    # Some知乎 APIs accept a 'publish' field directly
    pass


def main():
    cookies = load_cookies()
    if not cookies:
        print('ERROR: No知乎 cookies found')
        return 1

    print(f'Loaded {len(cookies)} cookies')

    # Check auth
    ok, info = check_auth(cookies)
    if ok:
        print(f'Auth OK: {info}')
    else:
        print(f'Auth FAILED: {info}')
        return 1

    # Publish drafts
    if len(sys.argv) > 1:
        media_ids = sys.argv[1:]
    else:
        # Default: try to publish the first draft
        media_ids = ['2044763924747245295']  # 避坑#30

    for mid in media_ids:
        print(f'\nPublishing draft {mid}...')
        success, msg = publish_draft(mid, cookies)
        icon = 'OK' if success else 'FAIL'
        print(f'  [{icon}] {msg}')

    return 0


def publish_all_drafts(cookies):
    """Publish all known draft media IDs."""
    # All media IDs from the publishing sessions
    media_ids = [
        "2044763924747245295", "2044764005076559605", "2044764012550820374",
        "2044764062530139836", "2044764070373487885", "2044764076048479962",
        "2044764129605448740", "2044764134428897465", "2044764140103799953",
        "2044764145778680237", "2044764219447448324", "2044764224983921709",
        "2044764230386184251", "2044764235864003777", "2044764241601856600",
        "2044764246920229837", "2044764252456609690", "2044764306521289410",
        "2044764311520794426", "2044764316881180148", "2044764322866496945",
        "2044764328197361844", "2044764333956191748", "2044764339291305088",
        "2044764383436395497", "2044764388708679683", "2044764394509403090",
        "2044764400125573042", "2044764406786028265", "2044764411781460494",
        "2044764542819886973", "2044764548352185936", "2044764553909647236",
        "2044764559228024245", "2044764603138193387", "2044764609152909700",
        "2044764614639055832", "2044764681085129695", "2044764687133365443",
        "2044764692619457261", "2044766328993666822", "2044766334563743736",
        "2044766341236880773", "2044766347075244096", "2044766389886571602",
        "2044766395469128395", "2044766400875582734", "2044766406269567794",
        "2044766414209291694", "2044766446681686458", "2044766452889257050",
        "2044766458580923515", "2044766463605609733", "2044766469360177728",
        "2044766476335313436", "2044767956660384246", "2044767963153264930",
        "2044767969352365580", "2044767975526462651", "2044767982321153785",
        "2044767988096685411", "2044768099044525607", "2044768104799002712",
        "2044768109844853797", "2044768115658159561", "2044768121190449998",
        "2044768125976056665", "2044768166178447548",
    ]

    success = 0
    fail = 0
    for mid in media_ids:
        ok, msg = publish_draft(mid, cookies)
        if ok:
            success += 1
        else:
            fail += 1
            print(f'  FAIL {mid}: {msg}')
        # Small delay to avoid rate limiting
        import time
        time.sleep(0.3)

    print(f'\n{"="*50}')
    print(f'  Published: {success}/{len(media_ids)}')
    print(f'  Failed: {fail}')
    print(f'{"="*50}')
    return success, fail


if __name__ == '__main__':
    cookies = load_cookies()
    if not cookies:
        print('ERROR: No知乎 cookies found')
        sys.exit(1)
    print(f'Loaded {len(cookies)} cookies')

    ok, info = check_auth(cookies)
    if not ok:
        print(f'Auth FAILED: {info}')
        sys.exit(1)
    print(f'Auth OK: {info}')

    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        publish_all_drafts(cookies)
    else:
        # Publish first article as test
        mid = sys.argv[1] if len(sys.argv) > 1 else '2044763924747245295'
        print(f'Publishing draft {mid}...')
        success, msg = publish_draft(mid, cookies)
        print(f'  [{"OK" if success else "FAIL"}] {msg}')
    sys.exit(0)
