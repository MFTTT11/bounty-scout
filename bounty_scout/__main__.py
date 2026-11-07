"""bounty-scout: list funded GitHub issues and whether they are worth a PR.

  python3 -m bounty_scout                         # all platforms
  python3 -m bounty_scout --platform lightningbounties --json
  GITHUB_TOKEN=... python3 -m bounty_scout        # higher rate limits
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .scan import PLATFORMS, scan


def main(argv=None):
    p = argparse.ArgumentParser(prog='bounty-scout', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--platform', choices=sorted(PLATFORMS), action='append')
    p.add_argument('--days', type=int, default=30, help='merge-proof window in days (default 30)')
    p.add_argument('--limit', type=int, default=10)
    p.add_argument('--json', action='store_true')
    a = p.parse_args(argv)
    rows, errors = scan(tuple(a.platform or PLATFORMS), os.environ.get('GITHUB_TOKEN'), days=a.days, limit=a.limit)
    if a.json:
        print(json.dumps({'results': rows, 'errors': errors}, indent=2))
    else:
        for r in rows:
            print(f"{r['score']:.2f} {r['verdict']:<14} {r['platform']:<17} competing={r['competing_prs']} {r['issue']}  {r['title']}")
        for e in errors:
            print('error:', e, file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
