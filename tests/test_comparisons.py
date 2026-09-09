import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import Mock, patch

import comparisons as comp
import news_sources
import web_discovery
from app import app


class ComparisonTest(unittest.TestCase):
    def setUp(self):
        batches = patch.object(news_sources, "BATCHES", ())
        batches.start()
        self.addCleanup(batches.stop)
        news_sources.cached_source.cache_clear()
        self.client = app.test_client()
        self.ids = list(comp.members())[:10]
        self.end = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)
        comp.collect.cache_clear()

    def test_every_period_accepts_five_and_ten_unique_members(self):
        for days in (90, 60, 30, 7, 1):
            for size in (5, 10):
                response = self.client.post('/api/compare/start', json={'days': days, 'member_ids': self.ids[:size]})
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                self.assertEqual(len(payload['members']), size)
                self.assertEqual(comp.date(payload['end_time']) - comp.date(payload['start_time']), timedelta(days=days))

    def test_rejects_duplicate_unknown_or_excessive_selection_and_invalid_period(self):
        for ids in ([self.ids[0]], [self.ids[0]] * 5, ['missing', self.ids[0]], list(comp.members())[:11]):
            self.assertEqual(self.client.post('/api/compare/start', json={'days': 30, 'member_ids': ids}).status_code, 400)
        for days in (60.0, True, 0, 120, '30', None):
            self.assertEqual(self.client.post('/api/compare/start', json={'days': days, 'member_ids': self.ids[:5]}).status_code, 400)

    def test_member_preserves_window_and_cache_without_calling_social_sources(self):
        start = self.client.post('/api/compare/start', json={'days': 60, 'territory': 'Antioquia', 'member_ids': self.ids[:5]}).get_json()
        with patch.object(comp, 'count_news', return_value=comp.available(17, 'Web')) as news, \
             patch.object(comp.requests, 'get', side_effect=AssertionError('Unexpected additional source')) as external:
            for member_id in self.ids[:5]:
                response = self.client.post('/api/compare/member', json={'member_id': member_id, 'days': 60, 'end_time': start['end_time'], 'territory': 'Antioquia'})
                self.assertEqual(response.status_code, 200)
                result = response.get_json()
                self.assertEqual(result['start_time'], start['start_time'])
                self.assertEqual(result['end_time'], start['end_time'])
                self.assertEqual(result['days'], 60)
                self.assertEqual(result['territory'], 'Antioquia')
                self.assertEqual(list(result['sources']), ['Web'])
                self.assertEqual(result['sources']['Web']['count'], 17)
            self.assertEqual(news.call_count, 5)
            self.assertTrue(all(call.args[1] == comp.date(start['start_time']) for call in news.call_args_list))
            self.client.post('/api/compare/member', json={'member_id': self.ids[0], 'days': 60, 'end_time': start['end_time'], 'territory': 'Antioquia'})
            self.assertEqual(news.call_count, 5, 'Identical windows use the cache')
            external.assert_not_called()

    def test_web_failure_is_unavailable_and_valid_empty_search_is_zero(self):
        start = self.client.post('/api/compare/start', json={'days': 1, 'member_ids': self.ids[:2]}).get_json()
        payload = {'member_id': self.ids[0], 'days': 1, 'end_time': start['end_time']}
        with patch.object(comp, 'count_news', side_effect=comp.requests.Timeout):
            result = self.client.post('/api/compare/member', json=payload).get_json()
        self.assertEqual(list(result['sources']), ['Web'])
        self.assertEqual(result['sources']['Web']['status'], 'unavailable')
        self.assertIsNone(result['sources']['Web']['count'])
        comp.collect.cache_clear()
        with patch.object(comp, 'count_news', return_value=comp.available(0, 'Sin noticias')):
            result = self.client.post('/api/compare/member', json=payload).get_json()
        self.assertEqual(result['sources']['Web']['status'], 'available')
        self.assertEqual(result['sources']['Web']['count'], 0)

    def test_expired_and_future_windows_are_rejected_before_source_calls(self):
        for end in (comp.iso(comp.now() - timedelta(hours=1)), comp.iso(comp.now() + timedelta(hours=1)), 'invalid'):
            with patch.object(comp, 'collect') as collect:
                response = self.client.post('/api/compare/member', json={'member_id': self.ids[0], 'days': 30, 'end_time': end})
                self.assertEqual(response.status_code, 400)
                collect.assert_not_called()

    def test_zone_applies_to_all_aliases_and_contains_no_injected_quotes(self):
        member = {'search_name': 'Alejandro Toro', 'full_name': 'David Alejandro Toro Ramírez', 'aliases': ['Alejandro Toro']}
        self.assertEqual(comp.query_for(member, 'Colombia'), news_sources.NewsQuery(('Alejandro Toro', 'David Alejandro Toro Ramírez'), 'Colombia'))

    def test_news_enforces_exact_last_24_hours_and_deduplicates(self):
        def item(title, date, link):
            return f'<item><title>{title}</title><link>{link}</link><pubDate>{format_datetime(date)}</pubDate></item>'
        xml = '<rss version="2.0"><channel><title>Results</title>'
        xml += item('Dentro', self.end - timedelta(hours=23), 'https://example.org/a')
        xml += item('Duplicado', self.end - timedelta(hours=23), 'https://example.org/a')
        xml += item('Fuera', self.end - timedelta(hours=25), 'https://example.org/b')
        xml += item('Posterior', self.end + timedelta(seconds=1), 'https://example.org/c')
        xml += '</channel></rss>'
        with patch.object(comp.requests, 'get', return_value=Mock(ok=True, content=xml.encode())), \
             patch.object(web_discovery, 'duckduckgo_web', return_value=([], 0, False)):
            result = comp.count_news('test', self.end - timedelta(days=1), self.end)
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['items'][0]['url'], 'https://example.org/a')
        news_sources.cached_source.cache_clear()
        with patch.object(comp.requests, 'get', return_value=Mock(ok=True, content=b'<html>Access denied</html>')):
            self.assertIsNone(comp.count_news('test', self.end - timedelta(days=1), self.end)['count'])

    def test_mi_red_is_replaced_and_sixty_days_is_in_both_forms(self):
        self.assertEqual(self.client.post('/api/mi-red', json={'username': 'test'}).status_code, 404)
        html = self.client.get('/').get_data(as_text=True)
        self.assertNotIn('MI RED', html)
        self.assertIn('COMPARATIVOS', html)
        self.assertEqual(html.count('<option value="60">60 días</option>'), 2)


if __name__ == '__main__':
    unittest.main()
