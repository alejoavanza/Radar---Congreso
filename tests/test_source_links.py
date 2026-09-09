import search_state
import unittest
from unittest.mock import Mock, patch

import app as radar
import news_sources
import web_discovery
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime


class SourceLinksTest(unittest.TestCase):
    def setUp(self):
        search_state.clear()
        news_sources.cached_source.cache_clear()
        batches = patch.object(news_sources, 'BATCHES', ())
        batches.start()
        self.addCleanup(batches.stop)

    def test_report_links_to_the_verified_original_article(self):
        article_url = 'https://news.google.com/rss/articles/CBMiExample?oc=5&hl=es-419'
        original_url = 'https://example.com/politica/alejandro-toro'
        html = '<meta property="article:published_time" content="' + (datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat() + '"><article>Alejandro Toro en Colombia</article>'
        feed = ('<rss version="2.0"><channel><item>'
                '<title>Alejandro Toro - Medio</title><pubDate>' + format_datetime((datetime.now(timezone.utc)-timedelta(minutes=5))) + '</pubDate>'
                '<link>' + article_url.replace('&', '&amp;') + '</link>'
                '<source url="https://example.com">Medio</source>'
                '</item></channel></rss>')
        response = Mock(content=feed.encode())
        with patch.object(news_sources.requests, 'get', return_value=response), \
             patch.object(web_discovery, 'duckduckgo_web', return_value=([], 0, False)), \
             patch.object(web_discovery, 'google_article', return_value=(original_url, html)):
            result = radar.app.test_client().post('/api/report', json={
                'name': 'Alejandro Toro', 'days': 30, 'territory': 'Colombia'
            })
        self.assertEqual(result.status_code, 200)
        item = result.get_json()['items'][0]
        self.assertEqual(item['url'], original_url)
        self.assertEqual(item['link'], original_url)

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
