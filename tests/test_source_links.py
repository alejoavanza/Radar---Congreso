import unittest
from unittest.mock import Mock, patch

import app as radar
import news_sources
from datetime import datetime, timezone
from email.utils import format_datetime


class SourceLinksTest(unittest.TestCase):
    def setUp(self):
        news_sources.cached_source.cache_clear()

    def test_report_keeps_the_exact_article_url_from_the_feed(self):
        article_url = 'https://news.google.com/rss/articles/CBMiExample?oc=5&hl=es-419'
        feed = ('<rss version="2.0"><channel><item>'
                '<title>Alejandro Toro - Medio</title><pubDate>' + format_datetime(datetime.now(timezone.utc)) + '</pubDate>'
                '<link>' + article_url.replace('&', '&amp;') + '</link>'
                '<source url="https://example.com">Medio</source>'
                '</item></channel></rss>')
        response = Mock(content=feed.encode())
        with patch.object(radar.requests, 'get', return_value=response), \
             patch.object(radar, 'fetch_bluesky_count', return_value=(0, 'error', None)), \
             patch.object(radar, 'fetch_reddit_count', return_value=(0, 'error', None)):
            result = radar.app.test_client().post('/api/report', json={
                'name': 'Alejandro Toro', 'days': 30, 'territory': 'Colombia'
            })
        self.assertEqual(result.status_code, 200)
        item = result.get_json()['items'][0]
        self.assertEqual(item['url'], article_url)
        self.assertEqual(item['link'], article_url)

    def test_broken_old_link_offers_a_route_back_to_the_report(self):
        response = radar.app.test_client().get('/undefined')
        self.assertEqual(response.status_code, 404)
        self.assertIn('Volver a mi consulta', response.get_data(as_text=True))
        self.assertIn('href="/"', response.get_data(as_text=True))

    def test_api_not_found_stays_machine_readable(self):
        response = radar.app.test_client().get('/api/undefined')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()['error'], 'Ruta no encontrada.')


if __name__ == '__main__':
    unittest.main()
