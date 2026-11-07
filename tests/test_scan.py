import datetime as dt
import unittest

from bounty_scout.scan import scan

NOW = dt.datetime(2026, 11, 7, tzinfo=dt.timezone.utc)
A = 'https://github.com/PrimalHQ/primal-web-app/issues/133'
B = 'https://github.com/acme/tool/issues/9'


def get(path, token):
    if path.startswith('/search/issues') and 'lightningbounties' in path:
        return {'items': [{'html_url': A, 'title': 'Add i18n'}, {'html_url': B, 'title': 'Fix crash'}]}
    if path == '/repos/PrimalHQ/primal-web-app/issues/133/comments?per_page=100':
        return [{'body': 'Funded: https://app.lightningbounties.com/x', 'html_url': A + '#issuecomment-1', 'user': {'login': 'lb'}}]
    if path == '/repos/acme/tool/issues/9/comments?per_page=100':
        return [{'body': 'Funded via app.lightningbounties.com', 'html_url': B + '#issuecomment-2', 'user': {'login': 'lb'}}]
    if 'is%3Aopen' in path and 'PrimalHQ' in path:
        return {'total_count': 0}
    if 'is%3Aopen' in path and 'acme' in path:
        return {'total_count': 2}
    if 'is%3Amerged' in path:
        return {'items': [{'html_url': 'https://github.com/x/y/pull/1'}]}
    raise AssertionError(path)


class ScanTest(unittest.TestCase):
    def test_ready_first_crowded_last(self):
        rows, errors = scan(('lightningbounties',), get=get, now=NOW, pause=lambda: None)
        self.assertEqual(errors, [])
        self.assertEqual([(r['issue'], r['verdict']) for r in rows], [(A, 'ready'), (B, 'crowded')])
        self.assertTrue(rows[0]['funding_comment'].endswith('#issuecomment-1'))


if __name__ == '__main__':
    unittest.main()
