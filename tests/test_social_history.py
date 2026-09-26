import csv
import io
import unittest
from datetime import date

from app import app
from comparisons import members
from social_history import COLUMNS, parse_export


class SocialHistoryTest(unittest.TestCase):
    def setUp(self):
        self.member = next(iter(members()))
        self.row = dict.fromkeys(COLUMNS, '')
        self.row.update(member_id=self.member, platform='instagram', account='@cuenta',
                        date='2026-09-01', followers='100', source='https://www.instagram.com/cuenta/')

    def csv(self, rows):
        output = io.StringIO(newline='')
        writer = csv.DictWriter(output, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    def parse(self, rows):
        return parse_export(self.csv(rows), members(), date(2026, 9, 25))

    def test_missing_is_not_zero_and_bom_roundtrip(self):
        row = {**self.row, 'views': '0'}
        parsed = parse_export('\ufeff' + self.csv([row]), members(), date(2026, 9, 25))[0]
        self.assertEqual(parsed['views'], 0)
        self.assertIsNone(parsed['reach'])
        self.assertEqual(parsed['followers'], 100)

    def test_rejects_fabricated_identity_dates_counts_and_unsafe_sources(self):
        for column, value in [('date', '2026-09-26'), ('date', '2026-02-30'), ('date', '20260901'),
                              ('platform', 'threads'), ('member_id', 'unknown'), ('followers', '-1'),
                              ('followers', '1.2'), ('followers', 'NaN'), ('followers', '1000000000001'),
                              ('source', 'javascript:alert(1)'), ('source', 'https://user:pass@host.test'),
                              ('account', '=FORMULA()')]:
            with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                self.parse([{**self.row, column: value}])

    def test_duplicates_and_account_switches_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicadas'):
            self.parse([self.row, self.row])
        with self.assertRaisesRegex(ValueError, 'dos cuentas'):
            self.parse([self.row, {**self.row, 'date': '2026-09-02', 'account': 'otra'}])

    def test_empty_metrics_and_malformed_csv(self):
        with self.assertRaises(ValueError):
            self.parse([{**self.row, 'followers': ''}])
        for text in ('member_id,platform\n', self.csv([self.row]) + 'a,b\n', 'a,a\n1,2\n'):
            with self.assertRaises(ValueError):
                parse_export(text, members(), date(2026, 9, 25))

    def test_http_import_is_private_no_store_and_does_not_publish_records(self):
        client = app.test_client()
        response = client.post('/api/social/import', data={'file': (io.BytesIO(self.csv([self.row]).encode()), 'datos.csv')})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json['persisted'])
        self.assertEqual(response.json['provenance'], 'user_import')
        self.assertEqual(response.headers['Cache-Control'], 'no-store, private')
        self.assertEqual(client.get('/api/social/import').status_code, 405)
        self.assertEqual(client.post('/api/social/import').status_code, 400)

    def test_size_limit_invalid_encoding_and_existing_pages(self):
        client = app.test_client()
        for content, status in [(b'\xff', 400), (b'a' * (2 * 1024 * 1024 + 1), 413)]:
            response = client.post('/api/social/import', data={'file': (io.BytesIO(content), 'datos.csv')})
            self.assertEqual(response.status_code, status)
        page = client.get('/')
        self.assertEqual(page.status_code, 200)
        # CSV compatibility remains server-side; the public screen now measures
        # followers and must not load the former illustrative demo controls.
        for id_ in ('report-tab', 'compare-tab', 'social-tab', 'followers-search', 'followers-results'):
            self.assertIn(f'id="{id_}"', page.text)
        self.assertNotIn('id="social-piece-example"', page.text)
        self.assertNotIn('/static/social-export.js', page.text)
        self.assertEqual(client.get('/health').json, {'status': 'ok'})


if __name__ == '__main__':
    unittest.main()
