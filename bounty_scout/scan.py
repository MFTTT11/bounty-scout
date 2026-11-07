"""Scan GitHub for issues whose comments link a bounty platform, and grade them.

Signals per issue (all from the GitHub API):
  funding     the comment that links the platform, and who wrote it
  competition open PRs in the repository that mention the issue number
  merge proof a PR by someone other than the owner merged in the last N days
Verdicts: "verified_ready" only when the funding comment comes from the platform's
official bot (algora-pbc[bot]) and there is merge proof and no competing PR;
"candidate" when the funding is only a link (not verified) or proof is missing;
"crowded" when other PRs exist. Ranking uses proven payment x completability x
low competition, never the claimed amount. The platform page is the final word
on amount and payout; check it before working.
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


# Accounts whose comment proves an active, funded bounty on that platform.
OFFICIAL_BOTS = {'algora': frozenset({'algora-pbc[bot]'})}


def _paged(get, path, token, pages, key=None, per_page=100):
    """Collect up to `pages` pages of a list or search endpoint."""
    out = []
    for page in range(1, pages + 1):
        sep = '&' if '?' in path else '?'
        data = get(f'{path}{sep}per_page={per_page}&page={page}', token)
        rows = data.get(key, []) if key else data
        if not isinstance(rows, list):
            break
        out.extend(rows)
        if len(rows) < per_page:
            break
    return out


def score(row):
    """Proven payment history x completability x low competition (claimed amounts are ignored)."""
    history = 1.0 if row['funding_verified'] else 0.4
    completable = 1.0 if row['merge_proof'] else 0.3
    competing = row['competing_prs']
    low_competition = 0.5 if competing is None else 1.0 / (1 + competing)
    return round(history * completable * low_competition, 3)


def scan(platforms=tuple(PLATFORMS), token=None, get=github_get, now=None, days=30, limit=10, pages=2,
         pause=lambda: time.sleep(2.2)):
    now = now or dt.datetime.now(dt.timezone.utc)
    since = (now - dt.timedelta(days=days)).date().isoformat()
    results, errors, seen = [], [], set()
    for platform in platforms:
        domain = PLATFORMS[platform]
        q = urllib.parse.urlencode({'q': f'"{domain}" in:comments is:issue is:open', 'sort': 'updated'})
        try:
            pause()
            items = _paged(get, '/search/issues?' + q, token, pages, key='items', per_page=limit)
        except (OSError, ValueError, AttributeError, TypeError) as exc:
            errors.append(f'{platform}: {type(exc).__name__}')
            continue
        for it in items:
            try:  # one broken issue must not stop the scan
                m = ISSUE.fullmatch(str(it.get('html_url', '')))
                if not m or m.group(0) in seen:
                    continue
                seen.add(m.group(0))
                owner, repo, number = m.group(1), m.group(2), int(m.group(3))
                full = f'{owner}/{repo}'
                comments = _paged(get, f'/repos/{full}/issues/{number}/comments', token, 3)
                funding = [c for c in comments if isinstance(c, dict) and domain in str(c.get('body', ''))]
                if not funding:
                    continue
                bots = OFFICIAL_BOTS.get(platform, frozenset())
                official = next((c for c in funding if (c.get('user') or {}).get('login') in bots), None)
                chosen = official or funding[-1]
                pause()
                competing = get('/search/issues?' + urllib.parse.urlencode({'q': f'repo:{full} is:pr is:open {number}'}), token).get('total_count')
                pause()
                merged = get('/search/issues?' + urllib.parse.urlencode(
                    {'q': f'repo:{full} is:pr is:merged merged:>={since} -author:{owner}', 'per_page': 1}), token)
                proof = (merged.get('items') or [None])[0]
                row = {'platform': platform, 'issue': m.group(0), 'title': str(it.get('title', ''))[:120],
                       'funding_comment': chosen.get('html_url'), 'funding_by': (chosen.get('user') or {}).get('login'),
                       'funding_verified': official is not None,
                       'competing_prs': competing if isinstance(competing, int) else None,
                       'merge_proof': (proof or {}).get('html_url')}
                if row['competing_prs']:
                    row['verdict'] = 'crowded'
                elif row['funding_verified'] and row['merge_proof'] and row['competing_prs'] == 0:
                    row['verdict'] = 'verified_ready'
                else:
                    row['verdict'] = 'candidate'
                row['score'] = score(row)
                results.append(row)
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                errors.append(f"{it.get('html_url') if isinstance(it, dict) else '?'}: {type(exc).__name__}")
    return sorted(results, key=lambda r: -r['score']), errors
