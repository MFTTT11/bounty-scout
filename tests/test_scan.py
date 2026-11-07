import datetime as dt
import unittest

from bounty_scout.scan import scan

NOW = dt.datetime(2026, 11, 7, tzinfo=dt.timezone.utc)
A = 'https://github.com/acme/app/issues/1'
B = 'https://github.com/acme/app/issues/2'
C = 'https://github.com/other/lib/issues/3'


def make_get(search_pages):
    def get(path, token):
        if path.startswith('/search/issues') and 'in%3Acomments' in path:
            page = int(path.rsplit('page=', 1)[1])
            return {'items': search_pages[page - 1] if page <= len(search_pages) else []}
        if path.startswith('/repos/acme/app/issues/1/comments'):
            return [{'body': 'Bounty $250 https://algora.io/acme/bounties/1', 'html_url': A + '#issuecomment-1', 'user': {'login': 'algora-pbc[bot]'}},
                    {'body': '/attempt #1', 'user': {'login': 'agent-x'}, 'author_association': 'NONE'}]
        if path.startswith('/repos/acme/app/issues/2/comments'):
            return [{'body': 'see algora.io for a bounty', 'html_url': B + '#issuecomment-2', 'user': {'login': 'random-user'}}]
        if path.startswith('/repos/other/lib/issues/3/comments'):
            raise ValueError('broken date in this issue')
        if 'is%3Aopen' in path:
            return {'total_count': 0}
        if 'is%3Amerged' in path:
            return {'items': [{'html_url': 'https://github.com/acme/app/pull/9'}]}
        raise AssertionError(path)
    return get


class ScanTest(unittest.TestCase):
    def test_only_official_bot_is_verified_and_link_only_is_candidate(self):
        get = make_get([[{'html_url': B, 'created_at': '2026-11-01T00:00:00Z'}, {'html_url': A, 'created_at': '2026-11-01T00:00:00Z'}]])
        rows, errors = scan(('algora',), get=get, now=NOW, pause=lambda: None, limit=2, pages=1)
        self.assertEqual(errors, [])
        self.assertEqual([(r['issue'], r['verdict']) for r in rows], [(A, 'verified_ready'), (B, 'candidate')])
        self.assertGreater(rows[0]['score'], rows[1]['score'])
        self.assertEqual((rows[0]['reward_usd'], rows[0]['agent_applicants'], rows[0]['gate_failed']), (250.0, 1, []))

    def test_stale_listing_is_not_ready(self):
        get = make_get([[{'html_url': A, 'created_at': '2020-01-01T00:00:00Z'}]])
        rows, _ = scan(('algora',), get=get, now=NOW, pause=lambda: None, limit=1, pages=1)
        self.assertEqual((rows[0]['verdict'], rows[0]['gate_failed']), ('candidate', ['stale listing']))

    def test_pagination_dedupe_and_error_isolation(self):
        get = make_get([[{'html_url': A}, {'html_url': C}], [{'html_url': A}, {'html_url': B}]])
        rows, errors = scan(('algora',), get=get, now=NOW, pause=lambda: None, limit=2, pages=2)
        self.assertEqual(sorted(r['issue'] for r in rows), [A, B])  # page 2 read, A once, C isolated
        self.assertEqual(len(errors), 1)
        self.assertIn('issues/3', errors[0])


if __name__ == '__main__':
    unittest.main()
