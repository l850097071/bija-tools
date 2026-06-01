#!/usr/bin/env python3
"""知乎草稿→公开发布工具 v2.0。修复: 需设置标题+话题再发布。"""
import json, sys, time, urllib.request, urllib.error
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "multi-publisher" / "config.json"


def load_cookies():
    with open(CONFIG_PATH, encoding='utf-8') as f:
        return json.load(f).get('zhihu', {}).get('cookies', {})


def cookie_str(cookies):
    return '; '.join(f'{k}={v}' for k, v in cookies.items())


def api_request(url, cookies, method='GET', data=None):
    headers = {
        'Cookie': cookie_str(cookies),
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'X-Requested-With': 'fetch',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    body = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read()), None
    except urllib.error.HTTPError as e:
        err = e.read().decode('utf-8') if e.fp else str(e)
        return e.code, None, err


def get_draft(media_id, cookies):
    """Get current draft state."""
    status, data, err = api_request(
        f'https://zhuanlan.zhihu.com/api/articles/{media_id}/draft',
        cookies
    )
    if status == 200 and data:
        return data
    return None


def update_draft(media_id, cookies, title, content, topics=None):
    """Update draft with full content and topics."""
    payload = {
        'title': title,
        'content': content,
    }
    if topics:
        payload['topics'] = topics

    status, data, err = api_request(
        f'https://zhuanlan.zhihu.com/api/articles/{media_id}/draft',
        cookies, method='PATCH', data=payload
    )
    return status in (200, 201, 204), status, err


def publish_draft_v2(media_id, cookies, title=None, topics=None):
    """Full publish flow: check draft → update → publish."""
    # Step 1: Get current draft state
    draft = get_draft(media_id, cookies)
    if not draft:
        print(f'  Cannot fetch draft {media_id}')
        return False

    current_title = draft.get('title', '')
    current_content = draft.get('content', '')
    current_topics = draft.get('topics', [])

    # Use provided or existing
    title = title or current_title
    topics = topics or current_topics

    # Step 2: If no topics, try to set a default one
    if not topics or len(topics) == 0:
        # Try to set a general DFT topic
        topics = [{'id': '19556686', 'name': '计算化学'}]  # Common topic ID
        # Update draft with topic
        ok, status, err = update_draft(media_id, cookies, title, current_content, topics)
        if not ok:
            print(f'  Topic update failed: HTTP {status} {err[:100] if err else ""}')
            # Continue anyway - might work without topics

    # Step 3: Publish!
    # Method A: PATCH with publish action
    status, data, err = api_request(
        f'https://zhuanlan.zhihu.com/api/articles/{media_id}/draft',
        cookies, method='PATCH',
        data={'action': 'publish', 'title': title, 'topics': topics}
    )
    if status in (200, 201, 204):
        # Verify
        draft2 = get_draft(media_id, cookies)
        if draft2:
            new_status = draft2.get('status', draft2.get('state', ''))
            is_pub = draft2.get('is_published', draft2.get('published', False))
            print(f'  Post-publish state: status={new_status}, is_published={is_pub}')
            if new_status != 'draft' or is_pub:
                return True
            else:
                print(f'  WARN: Still draft after publish attempt')

    # Method B: Try PUT with full article
    status2, data2, err2 = api_request(
        f'https://zhuanlan.zhihu.com/api/articles/{media_id}/draft',
        cookies, method='PUT',
        data={'title': title, 'content': current_content,
              'topics': topics, 'publish': True, 'status': 'published'}
    )
    if status2 in (200, 201, 204):
        print(f'  Method B (PUT) succeeded: HTTP {status2}')
        return True

    # Method C: Try POST to publish endpoint
    status3, data3, err3 = api_request(
        f'https://zhuanlan.zhihu.com/api/articles/{media_id}/publish',
        cookies, method='POST',
        data={'id': media_id, 'topics': topics}
    )
    if status3 in (200, 201, 204):
        print(f'  Method C (POST publish) succeeded: HTTP {status3}')
        return True

    print(f'  All methods failed: A=PATCH({status}) B=PUT({status2}) C=POST({status3})')
    return False


def publish_all(cookies):
    """Publish all known media IDs."""
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
        "2044768125976056665", "2044768166178447548", "2044770848754730352",
    ]

    success = 0
    for mid in media_ids:
        ok = publish_draft_v2(mid, cookies)
        if ok:
            success += 1
        else:
            # Try basic PATCH as fallback
            status, data, err = api_request(
                f'https://zhuanlan.zhihu.com/api/articles/{mid}/draft',
                cookies, method='PATCH', data={'action': 'publish'}
            )
            if status in (200, 201, 204):
                success += 1
            else:
                print(f'  FAIL {mid[-8:]}: all methods failed')
        time.sleep(0.3)

    print(f'\n{"="*50}')
    print(f'  Published: {success}/{len(media_ids)}')
    print(f'{"="*50}')
    return success


if __name__ == '__main__':
    cookies = load_cookies()
    if not cookies:
        print('ERROR: No cookies'), sys.exit(1)

    print(f'{len(cookies)} cookies loaded')

    if len(sys.argv) > 1:
        if sys.argv[1] == '--all':
            publish_all(cookies)
        elif sys.argv[1] == '--check':
            mid = sys.argv[2] if len(sys.argv) > 2 else '2044763924747245295'
            draft = get_draft(mid, cookies)
            if draft:
                print(f'Draft {mid}:')
                print(f'  status={draft.get("status", "?")}')
                print(f'  title={draft.get("title", "")[:80]}')
                print(f'  topics={draft.get("topics", [])}')
                print(f'  keys={list(draft.keys())}')
            else:
                print(f'Cannot fetch draft {mid}')
        else:
            mid = sys.argv[1]
            print(f'Publishing {mid}...')
            ok = publish_draft_v2(mid, cookies)
            print(f'  Result: {"OK" if ok else "FAIL"}')
    else:
        # Default: check first draft
        draft = get_draft('2044763924747245295', cookies)
        if draft:
            print(f'First draft status: {draft.get("status", "?")}')
            print(f'Title: {draft.get("title", "")[:100]}')
