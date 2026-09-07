import os
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from urllib.parse import urlparse

import app as radar
import news_sources
from email.utils import format_datetime


class RadarSourcesTest(unittest.TestCase):
    def setUp(self):
        news_sources.cached_source.cache_clear()

    @patch.dict(os.environ, {'X_BEARER_TOKEN': 'test-only-token'})
    def test_report_queries_remaining_sources_and_never_calls_x(self):
        now = datetime.now(timezone.utc)

        def source_response(url, **kwargs):
            host = urlparse(url).hostname
            if host == 'news.google.com':
                return Mock(content=b'<rss version="2.0"><channel><item><title>Una noticia</title>'
                            b'<link>https://example.org/noticia</link><pubDate>' + format_datetime(now).encode() + b'</pubDate></item></channel></rss>')
            if host == 'confidencialnoticias.com':
                return Mock(content=b'<rss version="2.0"><channel><title>Confidencial Noticias</title></channel></rss>')
            if host == 'www.lachivadeuraba.com':
                return Mock(content=b'<a href="/articulo/otra-noticia">Otra noticia</a>')
            if host == 'public.api.bsky.app':
                return Mock(json=lambda: {'posts': [{'uri': 'at://post/1', 'record': {'createdAt': now.isoformat()}}]})
            if host == 'www.reddit.com':
                return Mock(json=lambda: {'data': {'children': [{'data': {'name': 't3_1', 'created_utc': now.timestamp()}}]}})
            raise AssertionError('Unexpected source: ' + host)

        with patch.object(radar.requests, 'get', side_effect=source_response) as get:
            response = radar.app.test_client().post('/api/report', json={
                'name': 'Gustavo Petro', 'days': 30, 'territory': 'Colombia'
            })

        self.assertEqual(response.status_code, 200)
        mentions = response.get_json()['mentions']
        self.assertEqual(mentions['web'], 1)
        self.assertEqual(mentions['social'], 2)
        self.assertEqual(mentions['combined'], 3)
        self.assertCountEqual(mentions['active_sources'], ['Bluesky', 'Reddit'])
        self.assertNotIn('X', mentions['platform_counts'])
        self.assertNotIn('X', mentions['platform_status'])
        self.assertNotIn('X', mentions.get('diagnostics', {}))
        self.assertNotIn('x_intelligence', mentions)
        self.assertCountEqual([urlparse(call.args[0]).hostname for call in get.call_args_list],
                              ['news.google.com', 'confidencialnoticias.com', 'www.lachivadeuraba.com', 'public.api.bsky.app', 'www.reddit.com'])


if __name__ == '__main__':
    unittest.main()
