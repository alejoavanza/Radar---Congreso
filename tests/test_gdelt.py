import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

import app
import gdelt_source as gdelt
import news_sources as news
import search_state
import web_discovery as web
from territory_context import matches_territory, territory_query


class GdeltTest(unittest.TestCase):
    def setUp(self):
        search_state.clear()
        gdelt.cache.clear()
        gdelt._next_request = 0
        self.end = datetime(2026, 9, 24, 12, tzinfo=timezone.utc)
        self.start = self.end - timedelta(days=7)
        self.terms = ('Alejandro Toro', 'David Alejandro Toro Ramírez')
        self.row = {'url': 'https://international.example/politics/toro',
                    'title': 'Alejandro Toro meets lawmakers', 'seendate': '20260924100000',
                    'sourcecountry': 'United States', 'language': 'English'}

    def candidates(self, rows=None):
        with patch.object(gdelt, '_retrieve', return_value={'articles': rows or [self.row]}):
            return gdelt.gdelt_news(self.terms, 'Colombia', self.start, self.end)[0]

    def html(self, body, date='2026-09-23T10:00:00Z'):
        return '<script type="application/ld+json">' + json.dumps({
            '@type': 'NewsArticle', 'headline': self.row['title'],
            'articleBody': body, 'datePublished': date}) + '</script>'

    def test_query_searches_names_worldwide_and_caches_response(self):
        with patch.object(gdelt, '_retrieve', return_value={'articles': [self.row]}) as retrieve:
            for _ in range(2):
                found, skipped, capped = gdelt.gdelt_news(self.terms, 'Colombia', self.start, self.end)
        retrieve.assert_called_once()
        query = parse_qs(urlsplit(retrieve.call_args.args[0]).query)
        self.assertEqual(query['query'], ['("Alejandro Toro" OR "David Alejandro Toro Ramírez")'])
        self.assertNotIn('sourcecountry', str(query))
        self.assertNotIn('sourcelang', str(query))
        self.assertEqual(query['startdatetime'], ['20260917120000'])
        self.assertTrue(found[0]['candidate'])
        self.assertNotIn('published', found[0])
        self.assertEqual((skipped, capped), (0, False))

    def test_social_and_invalid_rows_are_not_candidates_and_cap_is_explicit(self):
        rows = [self.row] * 98 + [{'url': 'https://x.com/person/status/1', 'title': 'Social'}, None]
        with patch.object(gdelt, '_retrieve', return_value={'articles': rows}):
            found, skipped, capped = gdelt.gdelt_news(self.terms, 'Colombia', self.start, self.end)
        self.assertEqual(len(found), 98)
        self.assertEqual(skipped, 1)
        self.assertTrue(capped)

    def test_international_article_needs_original_name_context_and_date(self):
        candidate = self.candidates()[0]
        for body, date, accepted in (
            ('Colombian congressman Alejandro Toro speaks.', '2026-09-23T10:00:00Z', True),
            ('Le député colombien Alejandro Toro prend la parole.', '2026-09-23T10:00:00Z', True),
            ('Alejandro Toro visita Bogotá.', '2026-09-23T10:00:00Z', True),
            ('Alejandro Toro visita una escuela en España.', '2026-09-23T10:00:00Z', False),
            ('Alejandro Toro en Colombia.', None, False),
            ('Alejandro Toro en Colombia.', '2020-09-23T10:00:00Z', False),
        ):
            with self.subTest(body=body, date=date), patch.object(web, 'cached_page', return_value=(candidate['url'], self.html(body, date))):
                item, _ = web._verify_page(candidate, self.terms, self.start, self.end, 'Colombia')
                self.assertEqual(item is not None, accepted)
                if item:
                    self.assertEqual(item['discovery'], 'GDELT')
                    self.assertEqual(item['published'], date)
        with patch.object(web, 'cached_page', return_value=(candidate['url'], self.html('Colombia').replace('Alejandro Toro', 'Otra persona'))):
            self.assertIsNone(web._verify_page(candidate, self.terms, self.start, self.end, 'Colombia')[0])

    def test_colombia_clues_do_not_match_unrelated_zones_or_partial_words(self):
        for text in ('El congresista colombiano Alejandro Toro', 'Toro en Antioquia',
                     'El representante Toro visita Medellín', 'A Colombian congressman'):
            self.assertTrue(matches_territory(text, 'Colombia'))
        for text in ('Columbian university', 'Colombiafake', 'Toro visita Cartagena en España',
                     'Toro visita Medellín'):
            self.assertFalse(matches_territory(text, 'Colombia'))
        self.assertFalse(matches_territory('Toro en Bogotá', 'Antioquia'))
        self.assertTrue(matches_territory('Cualquier lugar', ''))
        self.assertIn('Colombian', territory_query('Colombia'))

    def test_gdelt_merges_with_existing_search_without_duplicate_mentions(self):
        candidate = self.candidates()[0]
        with patch.object(news, 'BATCHES', ()), \
             patch.object(news, 'gdelt_news', return_value=([candidate], 0, False)), \
             patch.object(news, 'google_news', return_value=([dict(candidate, engine='Google Noticias')], 0, False)), \
             patch.object(web, 'duckduckgo_web', return_value=([], 0, False)), \
             patch.object(web, 'cached_page', return_value=(candidate['url'], self.html('Colombian congressman Alejandro Toro'))):
            result = news.search_news(news.NewsQuery(self.terms, 'Colombia'), self.start, self.end)
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['items'][0]['url'], self.row['url'])
        self.assertIn('GDELT', [source['source'] for source in result['sources']])

    def test_gdelt_outage_keeps_other_results_and_is_visible(self):
        item = {'title': 'Alejandro Toro', 'url': self.row['url'], 'published': '2026-09-23T10:00:00Z',
                'source': 'Medio', 'discovery': 'Google Noticias'}
        with patch.object(news, 'BATCHES', ()), \
             patch.object(news, 'gdelt_news', side_effect=ValueError('HTTP 429')), \
             patch.object(news, 'google_news', return_value=([item], 0, False)), \
             patch.object(web, 'duckduckgo_web', return_value=([], 0, False)):
            result = news.search_news(news.NewsQuery(self.terms, 'Colombia'), self.start, self.end)
        self.assertEqual(result['count'], 1)
        self.assertTrue(result['limited'])
        self.assertIn('no disponibles GDELT', result['message'])

    def test_empty_other_indexes_and_gdelt_outage_are_not_zero_mentions(self):
        with patch.object(news, 'BATCHES', ()), \
             patch.object(news, 'gdelt_news', side_effect=ValueError('HTTP 429')), \
             patch.object(news, 'google_news', return_value=([], 0, False)), \
             patch.object(web, 'duckduckgo_web', return_value=([], 0, False)):
            result = news.search_news(news.NewsQuery(self.terms, 'Colombia'), self.start, self.end)
        self.assertIsNone(result['count'])
        self.assertEqual(result['status'], 'unavailable')

    def test_malformed_responses_and_rate_limit_are_not_cached_as_empty(self):
        for code, body in ((429, b'Please wait'), (200, b'Invalid query'), (200, b'{}')):
            gdelt._next_request = 0
            response = Mock(status_code=code)
            response.iter_content.return_value = [body]
            context = Mock()
            context.__enter__ = Mock(return_value=response)
            context.__exit__ = Mock(return_value=False)
            with patch.object(gdelt.requests, 'get', return_value=context) as get:
                with self.assertRaises(ValueError):
                    gdelt.gdelt_news(self.terms, 'Colombia', self.start, self.end)
                with self.assertRaises(ValueError):
                    gdelt.gdelt_news(self.terms, 'Colombia', self.start, self.end)
                self.assertEqual(get.call_count, 1)

    def test_transport_accepts_explicit_empty_and_rejects_oversized_response(self):
        for body, accepted in ((b'{"articles": []}', True), (b'x' * (gdelt.MAX_BYTES + 1), False)):
            gdelt._next_request = 0
            response = Mock(status_code=200)
            response.iter_content.return_value = [body]
            context = Mock()
            context.__enter__ = Mock(return_value=response)
            context.__exit__ = Mock(return_value=False)
            with patch.object(gdelt.requests, 'get', return_value=context):
                if accepted:
                    self.assertEqual(gdelt._retrieve(gdelt.API_URL), {'articles': []})
                else:
                    with self.assertRaises(ValueError):
                        gdelt._retrieve(gdelt.API_URL)

    def test_interface_explains_gdelt_and_on_demand_search(self):
        html = app.app.test_client().get('/').get_data(as_text=True)
        self.assertIn('GDELT', html)
        self.assertIn('sin alertas automáticas', html)
        self.assertIn('homónimos', html)

    def test_gdelt_cannot_displace_all_existing_index_candidates(self):
        found = [{'url': f'https://gdelt{i}.example/a', 'engine': 'GDELT', 'title': 'Nota'} for i in range(30)]
        found += [{'url': f'https://google{i}.example/a', 'engine': 'Google Noticias', 'title': 'Nota'} for i in range(30)]
        with patch.object(web, 'verify_page', return_value=(None, 0)) as verify:
            _, _, capped = web.verify_candidates(found, self.terms, self.start, self.end, 'Colombia')
        engines = [call.args[0]['engine'] for call in verify.call_args_list]
        self.assertEqual(engines.count('GDELT'), 12)
        self.assertEqual(engines.count('Google Noticias'), 12)
        self.assertTrue(capped)


if __name__ == '__main__':
    unittest.main()
