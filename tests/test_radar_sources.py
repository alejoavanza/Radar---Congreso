import os
import unittest
from datetime import datetime, timezone
from email.utils import format_datetime
from unittest.mock import Mock, patch
from urllib.parse import urlparse

import app as radar
import news_sources


class RadarSourcesTest(unittest.TestCase):
    def setUp(self):
        news_sources.cached_source.cache_clear()

    @patch.dict(os.environ, {'X_BEARER_TOKEN':'test-only-token', 'YOUTUBE_API_KEY':'test-only-key'})
    def test_report_only_contacts_news_publishers_and_has_no_social_metrics(self):
        published = format_datetime(datetime.now(timezone.utc)).encode()

        def source_response(url, **kwargs):
            host = urlparse(url).hostname
            if host == 'news.google.com':
                return Mock(content=b'<rss version="2.0"><channel><item><title>Una noticia</title>'
                            b'<link>https://example.org/noticia</link><pubDate>' + published + b'</pubDate></item></channel></rss>')
            if host == 'confidencialnoticias.com':
                return Mock(content=b'<rss version="2.0"><channel><title>Confidencial Noticias</title></channel></rss>')
            if host == 'www.lachivadeuraba.com':
                return Mock(content=b'<a href="/articulo/otra-noticia">Otra noticia</a>')
            raise AssertionError('Unexpected source: ' + host)

        with patch.object(news_sources.requests, 'get', side_effect=source_response) as get:
            response = radar.app.test_client().post('/api/report', json={
                'name':'Gustavo Petro', 'days':30, 'territory':'Colombia'
            })
        self.assertEqual(response.status_code, 200)
        mentions = response.json['mentions']
        self.assertEqual(mentions['web'], 1)
        self.assertEqual(mentions['combined'], 1)
        self.assertNotIn('social', mentions)
        self.assertNotIn('platform_counts', mentions)
        self.assertNotIn('platform_status', mentions)
        self.assertCountEqual([urlparse(call.args[0]).hostname for call in get.call_args_list],
                             ['news.google.com', 'confidencialnoticias.com', 'www.lachivadeuraba.com'])

    def test_report_surface_has_one_web_count_and_keeps_company_links(self):
        html = radar.app.test_client().get('/').get_data(as_text=True)
        self.assertIn('Publicaciones en medios web', html)
        self.assertNotIn('id="msocial"', html)
        self.assertNotIn('id="mcombined"', html)
        self.assertNotIn('Menciones en redes y web', html)
        self.assertIn('Sitio web de Táctika Comunicaciones', html)
        self.assertIn('Instagram de Táctika Comunicaciones', html)
        self.assertIn('Facebook de Táctika Comunicaciones', html)


if __name__ == '__main__':
    unittest.main()
