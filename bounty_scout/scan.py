"""Scan GitHub for issues whose comments link a bounty platform, and grade them.

Signals per issue (all from the GitHub API):
  funding     the comment that links the platform, and who wrote it
  competition open PRs in the repository that mention the issue number
  merge proof a PR by someone other than the owner merged in the last N days
Verdict: "ready" (funding + merge proof + no competing PR), "crowded" or "quiet_repo".
The platform's own page is the final word on amount and payout; check it before working.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
import urllib.parse
import urllib.request

PLATFORMS = {
    'lightningbounties': 'app.lightningbounties.com',
    'bountyhub': 'bountyhub.dev',
    'algora': 'algora.io',
}
ISSUE = re.compile(r'https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/([0-9]+)\Z')


def github_get(path, token=None, timeout=20):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'bounty-scout/0.1', 'X-GitHub-Api-Version': '2022-11-28'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    with urllib.request.urlopen(urllib.request.Request('https://api.github.com' + path, headers=headers), timeout=timeout) as r:
        return json.loads(r.read(5_000_001))


def scan(platforms=tuple(PLATFORMS), token=None, get=github_get, now=None, days=30, limit=10, pause=lambda: time.sleep(2.2)):
    now = now or dt.datetime.now(dt.timezone.utc)
    since = (now - dt.timedelta(days=days)).date().isoformat()
    results, errors = [], []
    for platform in platforms:
        domain = PLATFORMS[platform]
        q = f'"{domain}" in:comments is:issue is:open'
        try:
            pause()
            items = get('/search/issues?' + urllib.parse.urlencode({'q': q, 'sort': 'updated', 'per_page': limit}), token).get('items', [])
        except (OSError, ValueError, AttributeError) as exc:
            errors.append(f'{platform}: {type(exc).__name__}')
            continue
        for it in items[:limit]:
            m = ISSUE.fullmatch(str(it.get('html_url', '')))
            if not m:
                continue
            owner, repo, number = m.group(1), m.group(2), int(m.group(3))
            full = f'{owner}/{repo}'
            try:
                comments = get(f'/repos/{full}/issues/{number}/comments?per_page=100', token)
                funding = next((c for c in comments if isinstance(c, dict) and domain in str(c.get('body', ''))), None)
                if funding is None:
                    continue
                pause()
                competing = get('/search/issues?' + urllib.parse.urlencode({'q': f'repo:{full} is:pr is:open {number}'}), token).get('total_count')
                pause()
                merged = get('/search/issues?' + urllib.parse.urlencode(
                    {'q': f'repo:{full} is:pr is:merged merged:>={since} -author:{owner}', 'per_page': 1}), token)
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                errors.append(f'{full}#{number}: {type(exc).__name__}')
                continue
            proof = (merged.get('items') or [None])[0]
            verdict = 'ready' if competing == 0 and proof else ('crowded' if competing else 'quiet_repo')
            results.append({'platform': platform, 'issue': m.group(0), 'title': str(it.get('title', ''))[:120],
                            'funding_comment': funding.get('html_url'), 'funding_by': (funding.get('user') or {}).get('login'),
                            'competing_prs': competing, 'merge_proof': (proof or {}).get('html_url'), 'verdict': verdict})
    order = {'ready': 0, 'quiet_repo': 1, 'crowded': 2}
    return sorted(results, key=lambda r: order[r['verdict']]), errors
