import unittest
import json
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import Mock, patch

import news_sources as news
import app as radar


EMPTY = b'<rss version="2.0"><channel><title>Noticias</title></channel></rss>'
CONF_URL = 'https://confidencialnoticias.com/opinion/mientras-la-ia-corre-colombia-sigue-en-la-linea-de-salida-alejandro-toro/'
CHIVA_URL = 'https://www.lachivadeuraba.com/articulo/esposa-del-diputado-walter-salas-a-la-utl-de-alejandro-toro'


def rss(title, link, published, source='Medio', author=''):
    return ('<rss version="2.0"><channel><item><title>' + title + '</title><link>' + link +
            '</link><pubDate>' + format_datetime(published) + '</pubDate><source>' + source +
            '</source><author>' + author + '</author></item></channel></rss>').encode()


class NewsRegressionTest(unittest.TestCase):
    def setUp(self):
        news.cached_source.cache_clear()
        self.end = datetime(2026, 9, 7, 5, tzinfo=timezone.utc)
        self.start = self.end - timedelta(days=7)
        self.query = news.NewsQuery(('Alejandro Toro', 'David Alejandro Toro Ramírez'), 'Colombia')

    def test_full_name_without_results_cannot_erase_short_name_results(self):
        def response(url, **kwargs):
            query = kwargs['params']['q']
            self.assertNotIn(' OR ', query)
            self.assertIn('"Colombia"', query)
            return Mock(content=rss('Una mención', 'https://medio.co/nota', self.end-timedelta(days=2))
                        if query.startswith('"Alejandro Toro"') else EMPTY)

        with patch.object(news.requests, 'get', side_effect=response) as get, \
             patch.object(news, 'confidencial_news', return_value=([], 0, False)), \
             patch.object(news, 'chiva_news', return_value=([], 0, False)):
            result = news.search_news(self.query, self.start, self.end)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(result['count'], 1)

    def source_fixture(self, url):
        if url == news.CONF_FEED:
            return rss('Mientras la IA corre Colombia sigue en la línea de salida', CONF_URL,
                       datetime(2026, 9, 6, 6, 45, tzinfo=timezone.utc), 'Confidencial Noticias', 'Alejandro Toro')
        if url == news.CHIVA_HOME:
            return ('<a href="' + CHIVA_URL + '">Esposa del diputado Walter Salas a la UTL de Alejandro Toro</a>').encode()
        if url == CHIVA_URL:
            return b'<meta property="og:title" content="Esposa del diputado Walter Salas a la UTL de Alejandro Toro"><meta property="article:published_time" content="2026-09-04T02:49:32.605Z"><meta property="article:modified_time" content="2026-09-06T19:34:11.764Z">'
        raise AssertionError('Unapproved publisher URL: ' + url)

    def test_both_reported_articles_are_discovered_when_google_returns_zero(self):
        with patch.object(news, 'source_bytes', side_effect=self.source_fixture), \
             patch.object(news, 'google_news', return_value=([], 0, False)):
            result = news.search_news(self.query, self.start, self.end)
        self.assertEqual(result['count'], 2)
        self.assertEqual([item['url'] for item in result['items']], [CONF_URL, CHIVA_URL])
        self.assertTrue(result['items'][1]['published'].startswith('2026-09-04'))

    def test_last_24_hours_does_not_include_article_only_updated_yesterday(self):
        with patch.object(news, 'source_bytes', side_effect=self.source_fixture), \
             patch.object(news, 'google_news', return_value=([], 0, False)):
            result = news.search_news(self.query, self.end-timedelta(days=1), self.end)
        self.assertEqual([item['url'] for item in result['items']], [CONF_URL])

    def test_public_api_recovers_authored_column_when_feed_is_unavailable(self):
        post = {'status': 'publish', 'link': CONF_URL, 'slug': 'una-columna',
                'date_gmt': '2026-09-06T06:45:00',
                'title': {'rendered': 'Mientras la IA corre Colombia sigue en la línea de salida'},
                '_embedded': {'author': [{'name': 'Alejandro Toro'}]}}
        old = dict(post, link='https://confidencialnoticias.com/columna-anterior/',
                   date_gmt='2026-08-01T06:45:00', modified_gmt='2026-09-06T06:45:00')
        private = dict(post, status='private')
        forbidden = news.requests.HTTPError(response=Mock(status_code=403))
        with patch.object(news, 'source_bytes', side_effect=[forbidden, json.dumps([post, old, private]).encode()]):
            items, missing, limited = news.confidencial_news(self.query.terms, 'Colombia', self.start, self.end)
        self.assertEqual([item['url'] for item in items], [CONF_URL])
        self.assertEqual(items[0]['published'], '2026-09-06T06:45:00Z')
        self.assertEqual(missing, 0)
        self.assertFalse(limited)

    def test_api_access_error_is_unavailable_and_does_not_become_zero(self):
        forbidden = news.requests.HTTPError(response=Mock(status_code=403))
        with patch.object(news, 'get_bytes', side_effect=forbidden):
            result = news.search_news(self.query, self.start, self.end)
        self.assertEqual(result['status'], 'unavailable')
        self.assertIsNone(result['count'])

    def test_google_and_publisher_same_story_count_once_with_direct_url(self):
        title = 'Mientras la IA corre Colombia sigue en la línea de salida'
        google, _, _ = news.feed_items(rss(title + ' - Confidencial Noticias', 'https://news.google.com/rss/articles/fixture',
                                           datetime(2026, 9, 6, 6, 45, tzinfo=timezone.utc), 'Confidencial Noticias'), self.start, self.end)
        with patch.object(news, 'source_bytes', side_effect=self.source_fixture), \
             patch.object(news, 'google_news', return_value=(google, 0, False)):
            result = news.search_news(self.query, self.start, self.end)
        self.assertEqual(result['count'], 2)
        self.assertEqual(result['items'][0]['url'], CONF_URL)

    def test_failed_sources_are_unavailable_and_never_a_complete_zero(self):
        with patch.object(news, 'get_bytes', side_effect=news.requests.Timeout):
            result = news.search_news(self.query, self.start, self.end)
        self.assertIsNone(result['count'])
        self.assertEqual(result['status'], 'unavailable')
        with patch.object(news, 'get_bytes', side_effect=news.requests.Timeout), \
             patch.object(news, 'confidencial_news', return_value=([], 0, False)):
            result = news.search_news(self.query, self.start, self.end)
        self.assertEqual(result['count'], 0)
        self.assertTrue(result['limited'])
        self.assertIn('No se completaron', result['message'])

    def test_zone_and_word_boundaries_do_not_match_other_names_or_locations(self):
        self.assertFalse(news.matches('Alejandro Toros', ['Alejandro Toro']))
        self.assertTrue(news.matches('MARÍA JOSÉ', ['Maria Jose']))
        self.assertTrue(news.in_zone('Urabá tiene noticias locales', 'Colombia'))
        self.assertFalse(news.in_zone('Urabá tiene noticias locales', 'Bogotá'))

    def test_social_posts_indexed_by_google_are_excluded_from_web_count(self):
        raw = rss('Una publicación social', 'https://news.google.com/rss/articles/facebook-post',
                  self.end-timedelta(days=2), 'facebook.com')
        self.assertEqual(news.feed_items(raw, self.start, self.end)[0], [])
        self.assertTrue(news.social_result('https://m.facebook.com/noticia', {}))
        self.assertTrue(news.social_result('https://news.google.com/rss/articles/post', {'href':'https://www.instagram.com'}))
        self.assertFalse(news.social_result('https://medio.co/noticia-sobre-facebook', {'title':'Medio'}))

    def test_zero_report_explains_coverage_and_total_outage_returns_error(self):
        with patch.object(radar, 'fetch_news', return_value=([], None, {'status': 'available', 'message': 'Cobertura parcial'})):
            result = radar.app.test_client().post('/api/report', json={'name': 'Persona', 'days': 7})
        self.assertEqual(result.status_code, 200)
        self.assertIn('No se encontraron', result.json['summary'])
        self.assertNotIn('registra 0', result.json['summary'])
        with patch.object(radar, 'fetch_news', return_value=([], 'No disponible', {})):
            self.assertEqual(radar.app.test_client().post('/api/report', json={'name': 'Persona'}).status_code, 502)


if __name__ == '__main__':
    unittest.main()
